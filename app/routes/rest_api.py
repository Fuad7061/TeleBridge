from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import (
    check_password, create_session, delete_session,
    require_auth, get_session_token, validate_session, COOKIE_NAME,
)
from app.database import get_db
from app.state import get_worker

auth_router = APIRouter(prefix="/api/v1/auth")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_auth)])


class LoginRequest(BaseModel):
    password: str


@auth_router.post("/login")
async def api_login(data: LoginRequest, request: Request):
    if not check_password(data.password):
        raise HTTPException(401, "Invalid password")
    token = create_session()
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=COOKIE_NAME, value=token, max_age=86400 * 7,
        httponly=True, samesite="lax",
    )
    return response


@auth_router.post("/logout")
async def api_logout(request: Request):
    token = get_session_token(request)
    if token:
        delete_session(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME)
    return response


@auth_router.get("/check")
async def api_auth_check(request: Request):
    token = get_session_token(request)
    return {"authenticated": validate_session(token)}


# ─── Dashboard ──────────────────────────────────────────────────────────────

@router.get("/stats")
async def api_stats():
    db = await get_db()

    cursor = await db.execute("SELECT COUNT(*) as c FROM accounts")
    accounts_count = (await cursor.fetchone())["c"]

    cursor = await db.execute("SELECT COUNT(*) as c FROM forward_rules")
    rules_count = (await cursor.fetchone())["c"]

    cursor = await db.execute("SELECT COUNT(*) as c FROM forward_rules WHERE is_active = 1")
    active_rules = (await cursor.fetchone())["c"]

    cursor = await db.execute("SELECT COUNT(*) as c FROM forward_logs WHERE created_at >= datetime('now', '-24 hours')")
    last_24h = (await cursor.fetchone())["c"]

    cursor = await db.execute("SELECT COUNT(*) as c FROM forward_logs WHERE status = 'error' AND created_at >= datetime('now', '-24 hours')")
    errors_24h = (await cursor.fetchone())["c"]

    cursor = await db.execute(
        "SELECT fl.*, fr.name as rule_name FROM forward_logs fl "
        "JOIN forward_rules fr ON fl.rule_id = fr.id "
        "ORDER BY fl.created_at DESC LIMIT 10"
    )
    recent = [dict(r) for r in await cursor.fetchall()]

    await db.close()
    return {
        "accounts": accounts_count,
        "rules": rules_count,
        "active_rules": active_rules,
        "forwards_24h": last_24h,
        "errors_24h": errors_24h,
        "recent_activity": recent,
    }


# ─── Accounts ───────────────────────────────────────────────────────────────

@router.get("/accounts")
async def api_list_accounts():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM accounts ORDER BY created_at DESC")
    accounts = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return {"accounts": accounts}


@router.delete("/accounts/{account_id}")
async def api_delete_account(account_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT type FROM accounts WHERE id = ?", (account_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "Account not found")

    from app.state import get_worker
    w = get_worker()
    if w:
        await w.stop_account(account_id)

    await db.execute("DELETE FROM forward_rules WHERE source_account_id = ? OR dest_account_id = ?", (account_id, account_id))
    await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    await db.commit()
    await db.close()
    return {"ok": True}


# ─── Rules ──────────────────────────────────────────────────────────────────

@router.get("/rules")
async def api_list_rules():
    db = await get_db()
    cursor = await db.execute(
        """SELECT fr.*, src.name as source_account_name,
                  dst.name as dest_account_name
           FROM forward_rules fr
           LEFT JOIN accounts src ON fr.source_account_id = src.id
           LEFT JOIN accounts dst ON fr.dest_account_id = dst.id
           ORDER BY fr.created_at DESC"""
    )
    rules = [dict(r) for r in await cursor.fetchall()]

    cursor = await db.execute(
        "SELECT fr.id, COUNT(fl.id) as log_count FROM forward_rules fr "
        "LEFT JOIN forward_logs fl ON fl.rule_id = fr.id GROUP BY fr.id"
    )
    log_counts = {r["id"]: r["log_count"] for r in await cursor.fetchall()}
    await db.close()
    return {"rules": rules, "log_counts": log_counts}


class RuleCreate(BaseModel):
    name: str
    source_account_id: int
    source_chat_id: str
    source_chat_title: str = ""
    dest_account_id: int = 0
    dest_chat_id: str = ""
    dest_chat_title: str = ""
    delivery_agent: str = "account"
    forward_method: str = "copy"
    webhook_mode: str = "off"
    webhook_url: str = ""
    keyword_allow: str = ""
    keyword_block: str = ""
    media_types: str = "all"
    user_whitelist: str = ""
    user_blacklist: str = ""
    prefix_text: str = ""
    cooldown_seconds: int = 0
    schedule_from: str = ""
    schedule_to: str = ""


def _rule_fields(data) -> dict:
    return {
        "name": data.name,
        "source_account_id": data.source_account_id,
        "source_chat_id": data.source_chat_id,
        "source_chat_title": data.source_chat_title or None,
        "dest_account_id": data.dest_account_id if data.dest_account_id > 0 else None,
        "dest_chat_id": data.dest_chat_id or None,
        "dest_chat_title": data.dest_chat_title or None,
        "delivery_agent": data.delivery_agent,
        "forward_method": data.forward_method,
        "webhook_mode": data.webhook_mode,
        "webhook_url": data.webhook_url or None,
        "keyword_allow": data.keyword_allow or "",
        "keyword_block": data.keyword_block or "",
        "media_types": data.media_types or "all",
        "user_whitelist": data.user_whitelist or "",
        "user_blacklist": data.user_blacklist or "",
        "prefix_text": data.prefix_text or "",
        "cooldown_seconds": data.cooldown_seconds or 0,
        "schedule_from": data.schedule_from or "",
        "schedule_to": data.schedule_to or "",
    }


_RULE_COLS = """name, source_account_id, source_chat_id, source_chat_title,
    dest_account_id, dest_chat_id, dest_chat_title,
    delivery_agent, forward_method, webhook_mode, webhook_url,
    keyword_allow, keyword_block, media_types, user_whitelist, user_blacklist,
    prefix_text, cooldown_seconds, schedule_from, schedule_to"""


@router.post("/rules")
async def api_create_rule(data: RuleCreate):
    errors = {}
    if not data.name:
        errors["name"] = "Rule name is required"
    if not data.source_account_id:
        errors["source_account_id"] = "Source account is required"
    if not data.source_chat_id:
        errors["source_chat_id"] = "Source chat is required"
    if data.webhook_mode in ("passthrough", "destination") and not data.webhook_url:
        errors["webhook_url"] = "Webhook URL is required"
    if errors:
        return JSONResponse({"errors": errors}, status_code=422)

    f = _rule_fields(data)
    cols = _RULE_COLS.replace("\n", "").replace(" ", "")
    placeholders = ",".join("?" * 20)

    db = await get_db()
    cursor = await db.execute(
        f"INSERT INTO forward_rules ({cols}) VALUES ({placeholders})",
        tuple(f.values()),
    )
    rule_id = cursor.lastrowid
    await db.commit()
    await db.close()

    w = get_worker()
    if w:
        await w.reload_rules()

    return {"id": rule_id, "ok": True}


@router.put("/rules/{rule_id}")
async def api_update_rule(rule_id: int, data: RuleCreate):
    errors = {}
    if not data.name:
        errors["name"] = "Rule name is required"
    if not data.source_account_id:
        errors["source_account_id"] = "Source account is required"
    if not data.source_chat_id:
        errors["source_chat_id"] = "Source chat is required"
    if data.webhook_mode in ("passthrough", "destination") and not data.webhook_url:
        errors["webhook_url"] = "Webhook URL is required"
    if errors:
        return JSONResponse({"errors": errors}, status_code=422)

    f = _rule_fields(data)
    set_clause = ", ".join(f"{col}=?" for col in _RULE_COLS.split(","))

    db = await get_db()
    await db.execute(
        f"UPDATE forward_rules SET {set_clause} WHERE id=?",
        tuple(f.values()) + (rule_id,),
    )
    await db.commit()
    await db.close()

    w = get_worker()
    if w:
        await w.reload_rules()

    return {"ok": True}


@router.post("/rules/{rule_id}/toggle")
async def api_toggle_rule(rule_id: int):
    db = await get_db()
    cursor = await db.execute("SELECT is_active FROM forward_rules WHERE id = ?", (rule_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "Rule not found")
    new_val = 0 if row["is_active"] else 1
    await db.execute("UPDATE forward_rules SET is_active = ? WHERE id = ?", (new_val, rule_id))
    await db.commit()
    await db.close()

    w = get_worker()
    if w:
        await w.reload_rules()

    return {"is_active": bool(new_val)}


@router.delete("/rules/{rule_id}")
async def api_delete_rule(rule_id: int):
    db = await get_db()
    await db.execute("DELETE FROM forward_rules WHERE id = ?", (rule_id,))
    await db.commit()
    await db.close()

    w = get_worker()
    if w:
        await w.reload_rules()

    return {"ok": True}


@router.get("/rules/dialogs")
async def api_get_dialogs(account_id: int):
    w = get_worker()
    if not w:
        return {"dialogs": []}
    try:
        dialogs = await w.get_dialogs(account_id)
        return {"dialogs": dialogs}
    except Exception as e:
        raise HTTPException(400, str(e))


# ─── Logs ───────────────────────────────────────────────────────────────────

@router.get("/logs")
async def api_list_logs(rule_id: int = None, limit: int = 100):
    db = await get_db()
    if rule_id:
        cursor = await db.execute(
            "SELECT fl.*, fr.name as rule_name FROM forward_logs fl "
            "JOIN forward_rules fr ON fl.rule_id = fr.id "
            "WHERE fl.rule_id = ? ORDER BY fl.created_at DESC LIMIT ?",
            (rule_id, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT fl.*, fr.name as rule_name FROM forward_logs fl "
            "JOIN forward_rules fr ON fl.rule_id = fr.id "
            "ORDER BY fl.created_at DESC LIMIT ?",
            (limit,),
        )
    logs = [dict(r) for r in await cursor.fetchall()]
    await db.close()
    return {"logs": logs}


@router.delete("/logs")
async def api_clear_logs():
    db = await get_db()
    await db.execute("DELETE FROM forward_logs")
    await db.commit()
    await db.close()
    return {"ok": True}


# ─── Settings ───────────────────────────────────────────────────────────────

@router.get("/settings")
async def api_get_settings():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM webhook_configs ORDER BY name")
    webhooks = [dict(r) for r in await cursor.fetchall()]
    api_id = await (await db.execute("SELECT value FROM telegram_config WHERE key = 'api_id'")).fetchone()
    api_hash = await (await db.execute("SELECT value FROM telegram_config WHERE key = 'api_hash'")).fetchone()
    await db.close()
    return {
        "api_id": api_id["value"] if api_id else "",
        "api_hash": api_hash["value"] if api_hash else "",
        "webhooks": webhooks,
    }


class ApiConfig(BaseModel):
    api_id: str
    api_hash: str


@router.put("/settings/api")
async def api_save_api_config(data: ApiConfig):
    db = await get_db()
    await db.execute("INSERT OR REPLACE INTO telegram_config (key, value) VALUES ('api_id', ?)", (data.api_id.strip(),))
    await db.execute("INSERT OR REPLACE INTO telegram_config (key, value) VALUES ('api_hash', ?)", (data.api_hash.strip(),))
    await db.commit()
    await db.close()
    return {"ok": True}


class WebhookCreate(BaseModel):
    name: str
    url: str
    secret: str = ""


@router.post("/settings/webhooks")
async def api_create_webhook(data: WebhookCreate):
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO webhook_configs (name, url, secret) VALUES (?, ?, ?)",
        (data.name, data.url, data.secret or None),
    )
    wh_id = cursor.lastrowid
    await db.commit()
    await db.close()
    return {"id": wh_id, "ok": True}


@router.delete("/settings/webhooks/{webhook_id}")
async def api_delete_webhook(webhook_id: int):
    db = await get_db()
    await db.execute("DELETE FROM webhook_configs WHERE id = ?", (webhook_id,))
    await db.commit()
    await db.close()
    return {"ok": True}


@router.post("/settings/webhooks/{webhook_id}/test")
async def api_test_webhook(webhook_id: int):
    import httpx
    db = await get_db()
    cursor = await db.execute("SELECT url FROM webhook_configs WHERE id = ?", (webhook_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        raise HTTPException(404, "Webhook not found")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(row["url"], json={"event": "test", "message": "TeleBridge test"})
        return {"status": resp.status_code, "ok": resp.is_success}
    except httpx.RequestError as e:
        return {"status": 0, "ok": False, "error": str(e)}


# ─── Bot/User Account Auth ──────────────────────────────────────────────────

class BotToken(BaseModel):
    name: str = ""
    bot_token: str


@router.post("/accounts/bot")
async def api_add_bot(data: BotToken):
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from app.services.crypto import encrypt

    db = await get_db()
    cursor = await db.execute("SELECT value FROM telegram_config WHERE key = 'api_id'")
    api_id_row = await cursor.fetchone()
    cursor = await db.execute("SELECT value FROM telegram_config WHERE key = 'api_hash'")
    api_hash_row = await cursor.fetchone()
    await db.close()

    if not api_id_row or not api_hash_row:
        raise HTTPException(400, "Configure API ID and Hash in Settings first")

    api_id = int(api_id_row["value"])
    api_hash = api_hash_row["value"]

    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start(bot_token=data.bot_token)
        me = await client.get_me()
        bot_name = data.name or me.username or me.first_name
        await client.disconnect()
    except Exception as e:
        raise HTTPException(400, f"Failed to connect: {e}")

    encrypted = encrypt(data.bot_token)
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO accounts (type, name, token_or_session, status) VALUES (?, ?, ?, ?)",
        ("bot", bot_name, encrypted, "connected"),
    )
    account_id = cursor.lastrowid
    await db.commit()
    await db.close()

    w = get_worker()
    if w:
        await w.start_account({
            "id": account_id, "type": "bot", "name": bot_name,
            "token_or_session": encrypted, "phone": None,
            "api_id": None, "api_hash": None,
        })

    return {"id": account_id, "name": bot_name}


class SendCodeRequest(BaseModel):
    name: str
    phone: str


@router.post("/accounts/user/send-code")
async def api_send_code(data: SendCodeRequest):
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    db = await get_db()
    cursor = await db.execute("SELECT value FROM telegram_config WHERE key = 'api_id'")
    api_id_row = await cursor.fetchone()
    cursor = await db.execute("SELECT value FROM telegram_config WHERE key = 'api_hash'")
    api_hash_row = await cursor.fetchone()
    await db.close()

    if not api_id_row or not api_hash_row:
        raise HTTPException(400, "Configure API ID and Hash in Settings first")

    api_id = int(api_id_row["value"])
    api_hash = api_hash_row["value"]

    from app.state import _pending_auth
    pending = _pending_auth

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    sent = await client.send_code_request(data.phone)

    pending["client"] = client
    pending["phone"] = data.phone
    pending["name"] = data.name
    pending["api_id"] = api_id
    pending["api_hash"] = api_hash
    pending["phone_code_hash"] = sent.phone_code_hash

    return {"ok": True, "hint": getattr(sent, "type", None)}


class VerifyCode(BaseModel):
    code: str
    password: str = ""


@router.post("/accounts/user/verify")
async def api_verify_code(data: VerifyCode):
    from app.services.crypto import encrypt
    from app.state import _pending_auth
    pending = _pending_auth

    client = pending.get("client")
    if not client:
        raise HTTPException(400, "No pending verification")

    phone = pending["phone"]
    name = pending["name"]
    phone_code_hash = pending["phone_code_hash"]
    api_id = pending["api_id"]
    api_hash = pending["api_hash"]

    try:
        await client.sign_in(phone, data.code, phone_code_hash=phone_code_hash)
    except Exception as e:
        err_str = str(e).upper()
        if "PASSWORD" in err_str and data.password:
            try:
                await client.sign_in(password=data.password)
            except Exception as e2:
                raise HTTPException(400, f"2FA failed: {e2}")
        elif "PASSWORD" in err_str:
            raise HTTPException(400, "2FA_REQUIRED")
        else:
            raise HTTPException(400, str(e))

    me = await client.get_me()
    display_name = name or me.first_name or me.username or str(me.id)
    session_str = client.session.save()
    await client.disconnect()

    encrypted = encrypt(session_str)
    db = await get_db()
    cursor = await db.execute(
        "INSERT INTO accounts (type, name, token_or_session, phone, api_id, api_hash, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("user", display_name, encrypted, phone, api_id, api_hash, "connected"),
    )
    account_id = cursor.lastrowid
    await db.commit()
    await db.close()

    pending.clear()

    w = get_worker()
    if w:
        await w.start_account({
            "id": account_id, "type": "user", "name": display_name,
            "token_or_session": encrypted, "phone": phone,
            "api_id": api_id, "api_hash": api_hash,
        })

    return {"id": account_id, "name": display_name}
