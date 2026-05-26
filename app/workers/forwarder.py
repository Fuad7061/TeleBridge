import asyncio
import re
import time
from datetime import datetime, time as dt_time

from telethon import TelegramClient
from telethon.events import NewMessage

from app.database import get_db
from app.services.webhook_sender import send_to_webhook


class MessageForwarder:
    def __init__(self):
        self._rules_cache = {}
        self._lock = asyncio.Lock()
        self._cooldown: dict[int, set[str]] = {}

    async def load_rules(self):
        async with self._lock:
            db = await get_db()
            cursor = await db.execute(
                "SELECT * FROM forward_rules WHERE is_active = 1"
            )
            rows = await cursor.fetchall()
            await db.close()

            cache = {}
            for row in rows:
                r = dict(row)
                key = (r["source_account_id"], str(r["source_chat_id"]))
                cache.setdefault(key, []).append(r)
            self._rules_cache = cache

    def _get_matching_rules(self, account_id: int, source_chat_id: str):
        return self._rules_cache.get((account_id, source_chat_id), [])

    async def handle_telethon_message(
        self, event: NewMessage.Event, account_id: int
    ):
        msg = event.message
        if not msg or msg.out:
            return

        source_chat_id = str(event.chat_id)
        rules = self._get_matching_rules(account_id, source_chat_id)
        if not rules:
            return

        client: TelegramClient = event.client

        for rule in rules:
            if not await self._check_filters(rule, msg, account_id):
                continue
            await self._process_rule(rule, client, None, msg, account_id)

    async def handle_bot_message(self, update, context, account_id: int):
        msg = update.message
        if not msg:
            return

        source_chat_id = str(msg.chat_id)
        rules = self._get_matching_rules(account_id, source_chat_id)
        if not rules:
            return

        for rule in rules:
            if not await self._check_filters(rule, msg, account_id):
                continue
            await self._process_rule(rule, None, context.bot, msg, account_id)

    async def _check_filters(self, rule: dict, msg, account_id: int) -> bool:
        text = msg.text or msg.caption or ""

        if rule.get("keyword_allow"):
            keywords = [k.strip().lower() for k in rule["keyword_allow"].split(",") if k.strip()]
            if keywords and not any(k in text.lower() for k in keywords):
                return False

        if rule.get("keyword_block"):
            keywords = [k.strip().lower() for k in rule["keyword_block"].split(",") if k.strip()]
            if keywords and any(k in text.lower() for k in keywords):
                return False

        media_types = rule.get("media_types", "all")
        if media_types and media_types != "all":
            allowed = set(m.strip() for m in media_types.split(",") if m.strip())
            has_media = bool(msg.media)
            if not has_media:
                if "text" not in allowed:
                    return False
            else:
                msg_type = self._detect_media_type(msg)
                if msg_type not in allowed:
                    return False

        if rule.get("user_whitelist"):
            allowed_ids = set(str(int(u.strip())) for u in rule["user_whitelist"].split(",") if u.strip())
            sender_id = str(getattr(msg, "from_id", None) or getattr(msg, "sender_id", None) or "")
            if allowed_ids and sender_id not in allowed_ids:
                return False

        if rule.get("user_blacklist"):
            blocked_ids = set(str(int(u.strip())) for u in rule["user_blacklist"].split(",") if u.strip())
            sender_id = str(getattr(msg, "from_id", None) or getattr(msg, "sender_id", None) or "")
            if blocked_ids and sender_id in blocked_ids:
                return False

        if rule.get("schedule_from") and rule.get("schedule_to"):
            now = datetime.now().time()
            try:
                sf = dt_time.fromisoformat(rule["schedule_from"])
                st = dt_time.fromisoformat(rule["schedule_to"])
                if sf <= st:
                    if not (sf <= now <= st):
                        return False
                else:
                    if not (now >= sf or now <= st):
                        return False
            except (ValueError, TypeError):
                pass

        msg_id = getattr(msg, "id", None) or getattr(msg, "message_id", None)
        cooldown = rule.get("cooldown_seconds", 0)
        if cooldown and msg_id:
            rule_id = rule["id"]
            if rule_id not in self._cooldown:
                self._cooldown[rule_id] = set()
            key = f"{msg_id}"
            if key in self._cooldown[rule_id]:
                return False
            self._cooldown[rule_id].add(key)
            asyncio.get_event_loop().call_later(cooldown, lambda: self._cooldown.get(rule_id, set()).discard(key))

        return True

    def _detect_media_type(self, msg) -> str:
        if hasattr(msg, "photo") and msg.photo:
            return "photo"
        if hasattr(msg, "video") and msg.video:
            return "video"
        if hasattr(msg, "document") and msg.document:
            return "document"
        if hasattr(msg, "audio") and msg.audio:
            return "audio"
        if hasattr(msg, "voice") and msg.voice:
            return "audio"
        return "other"

    def _apply_prefix(self, text: str, rule: dict) -> str:
        prefix = rule.get("prefix_text", "")
        if prefix:
            return f"{prefix}\n\n{text}"
        return text

    async def _copy_via_client(self, client, dest_chat_id, msg, prefix=""):
        text = msg.text or msg.message or ""
        text = self._apply_prefix(text, {"prefix_text": prefix}) if prefix else text
        if msg.media:
            file = await client.download_media(msg, file=bytes)
            await client.send_file(int(dest_chat_id), file, caption=text)
        else:
            await client.send_message(int(dest_chat_id), text)

    async def _forward_via_client(self, client, dest_chat_id, msg):
        await client.forward_messages(int(dest_chat_id), msg.id, msg.chat_id)

    async def _copy_via_bot(self, bot, dest_chat_id, text, photo=None, video=None, document=None, audio=None):
        if photo or video or document or audio:
            source = photo or video or document or audio
            if isinstance(source, bytes):
                from io import BytesIO
                buf = BytesIO(source)
                buf.seek(0)
                await bot.send_document(
                    chat_id=int(dest_chat_id), document=buf, caption=text,
                )
            else:
                file = await source.get_file()
                from io import BytesIO
                buf = BytesIO()
                await file.download_to_memory(buf)
                buf.seek(0)
                await bot.send_document(
                    chat_id=int(dest_chat_id), document=buf, caption=text,
                )
        else:
            await bot.send_message(chat_id=int(dest_chat_id), text=text)

    async def _forward_via_bot(self, bot, dest_chat_id, from_chat_id, message_id):
        await bot.forward_message(
            chat_id=int(dest_chat_id),
            from_chat_id=from_chat_id,
            message_id=message_id,
        )

    def _extract_bot_args(self, msg):
        text = msg.text or msg.caption or ""
        photo = getattr(msg, "photo", None)
        video = getattr(msg, "video", None)
        document = getattr(msg, "document", None)
        audio = getattr(msg, "audio", None)
        return text, photo, video, document, audio

    async def _send_to_telegram(
        self, client, bot, dest_chat_id, msg, delivery_agent, forward_method, prefix_text
    ):
        if forward_method == "copy":
            if delivery_agent == "bot":
                text, photo, video, document, audio = self._extract_bot_args(msg)
                text = self._apply_prefix(text, {"prefix_text": prefix_text}) if prefix_text else text
                await self._copy_via_bot(bot, dest_chat_id, text, photo, video, document, audio)
            else:
                await self._copy_via_client(client, dest_chat_id, msg, prefix_text)
        elif forward_method == "forward":
            if delivery_agent == "bot":
                from_chat_id = msg.chat_id
                message_id = msg.message_id
                await self._forward_via_bot(bot, dest_chat_id, from_chat_id, message_id)
            else:
                await self._forward_via_client(client, dest_chat_id, msg)
        elif forward_method == "forward_fallback_copy":
            try:
                if delivery_agent == "bot":
                    from_chat_id = msg.chat_id
                    message_id = msg.message_id
                    await self._forward_via_bot(bot, dest_chat_id, from_chat_id, message_id)
                else:
                    await self._forward_via_client(client, dest_chat_id, msg)
            except Exception:
                if delivery_agent == "bot":
                    text, photo, video, document, audio = self._extract_bot_args(msg)
                    text = self._apply_prefix(text, {"prefix_text": prefix_text}) if prefix_text else text
                    await self._copy_via_bot(bot, dest_chat_id, text, photo, video, document, audio)
                else:
                    await self._copy_via_client(client, dest_chat_id, msg, prefix_text)

    async def _send_to_webhook(self, rule: dict, msg, account_id: int):
        source_title = rule.get("source_chat_title", "Unknown")
        text = ""
        if hasattr(msg, "text"):
            text = msg.text or ""
        elif hasattr(msg, "message"):
            text = msg.message or ""

        payload = {
            "event": "message.forwarded",
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "source": {
                "account_id": account_id,
                "chat_id": str(rule["source_chat_id"]),
                "chat_title": source_title,
            },
            "message": {
                "id": getattr(msg, "id", None) or getattr(msg, "message_id", None),
                "text": text,
                "date": str(getattr(msg, "date", datetime.now())),
                "has_media": bool(getattr(msg, "media", None)),
            },
            "timestamp": datetime.now().isoformat(),
        }

        success, error = await send_to_webhook(rule["webhook_url"], payload)
        return success, error

    async def _process_rule(self, rule, client, bot, msg, account_id):
        webhook_mode = rule.get("webhook_mode", "off")
        dest_chat_id = rule.get("dest_chat_id")
        delivery_agent = rule.get("delivery_agent", "account")
        forward_method = rule.get("forward_method", "copy")
        prefix_text = rule.get("prefix_text", "")

        needs_client = delivery_agent == "account" or delivery_agent == "account_fallback_bot"
        needs_bot = delivery_agent == "bot" or delivery_agent == "account_fallback_bot"

        start = time.time()
        errors = []
        dest_info = []

        if webhook_mode in ("passthrough", "destination") and rule.get("webhook_url"):
            success, error = await self._send_to_webhook(rule, msg, account_id)
            if success:
                dest_info.append("webhook:ok")
            else:
                dest_info.append(f"webhook:fail")
                errors.append(f"webhook:{error}")
            if webhook_mode == "destination":
                pass

        if (webhook_mode != "destination") and dest_chat_id:
            try:
                if delivery_agent == "account":
                    if not client:
                        errors.append("tg:no_client_available")
                        dest_info.append("tg:skip")
                    else:
                        await self._send_to_telegram(
                            client, None, dest_chat_id, msg, delivery_agent, forward_method, prefix_text
                        )
                        dest_info.append(f"tg:{dest_chat_id}")
                elif delivery_agent == "bot":
                    if not bot:
                        errors.append("tg:no_bot_available")
                        dest_info.append("tg:skip")
                    else:
                        await self._send_to_telegram(
                            None, bot, dest_chat_id, msg, delivery_agent, forward_method, prefix_text
                        )
                        dest_info.append(f"tg:{dest_chat_id}")
                elif delivery_agent == "account_fallback_bot":
                    if not client and not bot:
                        errors.append("tg:no_agent_available")
                        dest_info.append("tg:skip")
                    elif client:
                        try:
                            await self._send_to_telegram(
                                client, None, dest_chat_id, msg, "account", forward_method, prefix_text
                            )
                            dest_info.append(f"tg:{dest_chat_id}")
                        except Exception as e:
                            err_str = str(e).lower()
                            if "flood" in err_str and bot:
                                await self._send_to_telegram(
                                    None, bot, dest_chat_id, msg, "bot", forward_method, prefix_text
                                )
                                dest_info.append(f"tg:{dest_chat_id}(bot_fallback)")
                            else:
                                raise
                    else:
                        await self._send_to_telegram(
                            None, bot, dest_chat_id, msg, "bot", forward_method, prefix_text
                        )
                        dest_info.append(f"tg:{dest_chat_id}(bot_fallback)")
            except Exception as e:
                dest_info.append(f"tg:fail")
                errors.append(f"tg:{e}")

        latency = int((time.time() - start) * 1000)
        status = "error" if errors else "success"

        msg_text = (getattr(msg, "text", None) or getattr(msg, "caption", None) or "")[:500]
        msg_media = self._detect_media_type(msg) if getattr(msg, "media", None) else ""

        db = await get_db()
        await db.execute(
            "INSERT INTO forward_logs (rule_id, source_msg_id, source_chat_title, message_text, message_media_type, dest_info, status, error, latency_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rule["id"],
                getattr(msg, "id", None) or getattr(msg, "message_id", None),
                rule.get("source_chat_title", ""),
                msg_text,
                msg_media,
                ", ".join(dest_info),
                status,
                "; ".join(errors) if errors else None,
                latency,
            ),
        )
        await db.execute(
            "DELETE FROM forward_logs WHERE id NOT IN (SELECT id FROM forward_logs ORDER BY id DESC LIMIT 100)"
        )
        await db.commit()
        await db.close()
