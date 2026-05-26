import asyncio
import logging

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Update
from telegram.ext import Application, MessageHandler, filters

from app.database import get_db
from app.services.crypto import decrypt
from app.workers.forwarder import MessageForwarder

logger = logging.getLogger(__name__)


class TelegramWorker:
    def __init__(self):
        self.telethon_clients: dict[int, TelegramClient] = {}
        self.bot_applications: dict[int, Application] = {}
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self.forwarder = MessageForwarder()
        self._account_names: dict[int, str] = {}
        self._reconnect_delays = [1, 5, 15, 30, 60, 120]

    async def start_all(self):
        await self.forwarder.load_rules()
        db = await get_db()
        cursor = await db.execute("SELECT * FROM accounts WHERE status = 'connected'")
        accounts = [dict(r) for r in await cursor.fetchall()]
        await db.close()

        for acc in accounts:
            try:
                await self.start_account(acc)
            except Exception as e:
                logger.error(f"Failed to start account {acc['id']} ({acc['name']}): {e}")

    async def start_account(self, acc: dict):
        account_id = acc["id"]
        self._account_names[account_id] = acc["name"]

        if acc["type"] == "user":
            session_encrypted = acc.get("token_or_session")
            if not session_encrypted:
                return
            session_str = decrypt(session_encrypted)
            api_id = acc.get("api_id")
            api_hash = acc.get("api_hash")
            if not api_id or not api_hash:
                return

            client = TelegramClient(
                StringSession(session_str),
                api_id=api_id,
                api_hash=api_hash,
                flood_sleep_threshold=60,
            )
            await client.start()
            self.telethon_clients[account_id] = client

            @client.on(events.NewMessage)
            async def handler(event, aid=account_id):
                try:
                    await self.forwarder.handle_telethon_message(event, aid)
                except Exception as e:
                    logger.error(f"Forward handler error for account {aid}: {e}")

            task = asyncio.create_task(self._run_telethon_reconnect(account_id, client))
            self._tasks.append(task)

        elif acc["type"] == "bot":
            token_encrypted = acc.get("token_or_session")
            if not token_encrypted:
                return
            token = decrypt(token_encrypted)

            app = Application.builder().token(token).build()

            async def bot_handler(update: Update, context, aid=account_id):
                try:
                    await self.forwarder.handle_bot_message(update, context, aid)
                except Exception as e:
                    logger.error(f"Bot handler error for account {aid}: {e}")

            app.add_handler(MessageHandler(filters.ALL, bot_handler))
            await app.initialize()
            await app.start()
            await app.updater.start_polling()
            self.bot_applications[account_id] = app

            task = asyncio.create_task(self._keep_bot_alive(account_id, app))
            self._tasks.append(task)

    async def _run_telethon_reconnect(self, account_id: int, client: TelegramClient):
        attempt = 0
        while not self._stop_event.is_set():
            try:
                attempt += 1
                await client.run_until_disconnected()
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                delay = self._reconnect_delays[min(attempt, len(self._reconnect_delays) - 1)]
                logger.warning(
                    f"Telethon account {account_id} disconnected (attempt {attempt}): {e}. "
                    f"Reconnecting in {delay}s..."
                )
                await asyncio.sleep(delay)

    async def _keep_bot_alive(self, account_id: int, app: Application):
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass

    async def stop_account(self, account_id: int):
        if account_id in self.telethon_clients:
            client = self.telethon_clients.pop(account_id)
            try:
                await client.disconnect()
            except Exception:
                pass

        if account_id in self.bot_applications:
            app = self.bot_applications.pop(account_id)
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception:
                pass

    async def stop_all(self):
        self._stop_event.set()
        for account_id in list(self.telethon_clients.keys()):
            await self.stop_account(account_id)
        for account_id in list(self.bot_applications.keys()):
            await self.stop_account(account_id)
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def reload_rules(self):
        await self.forwarder.load_rules()

    async def get_dialogs(self, account_id: int) -> list[dict]:
        if account_id in self.telethon_clients:
            client = self.telethon_clients[account_id]
            dialogs = await client.get_dialogs()
            result = []
            for d in dialogs:
                result.append({
                    "chat_id": str(d.id),
                    "title": d.title or d.name or "Unknown",
                    "type": self._chat_type(d.entity),
                    "username": getattr(d.entity, "username", None) or "",
                })
            return result
        if account_id in self.bot_applications:
            return []
        return []

    def _chat_type(self, entity) -> str:
        from telethon.tl.types import (
            Channel, Chat, User, ChatForbidden, ChannelForbidden,
        )
        if isinstance(entity, User):
            return "user"
        if isinstance(entity, Chat):
            return "group"
        if isinstance(entity, Channel):
            if getattr(entity, "megagroup", False):
                return "group"
            return "channel"
        if isinstance(entity, ChatForbidden):
            return "group"
        if isinstance(entity, ChannelForbidden):
            return "channel"
        return "unknown"
