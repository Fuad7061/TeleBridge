import asyncio
import httpx
import urllib.parse

from app.database import get_db


def _payload_to_query(payload: dict) -> str:
    params = {}
    def _flatten(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _flatten(v, f"{prefix}{k}." if prefix else f"{k}.")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _flatten(v, f"{prefix}{i}." if prefix else f"{i}.")
        else:
            params[prefix.rstrip(".")] = str(obj)
    _flatten(payload)
    return urllib.parse.urlencode(params)


async def _try_method(
    client: httpx.AsyncClient, method: str, url: str, payload: dict
) -> httpx.Response:
    if method == "POST":
        return await client.post(url, json=payload)
    query = _payload_to_query(payload)
    sep = "&" if "?" in url else "?"
    return await client.get(f"{url}{sep}{query}")


async def send_to_webhook(webhook_url: str, payload: dict) -> tuple[bool, str | None]:
    methods = ["POST", "GET"]
    last_err = ""

    for method in methods:
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await _try_method(client, method, webhook_url, payload)
                    if resp.is_success:
                        return True, None
                    last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    body = resp.text[:200].lower()
                    if method == "POST" and ("get request" in body or ("get" in body and "post" in body)):
                        break
                    if attempt == 0:
                        await asyncio.sleep(1)
            except httpx.RequestError as e:
                last_err = str(e)
                if attempt == 0:
                    await asyncio.sleep(1)

    return False, last_err


async def get_webhook_configs() -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, name, url, is_active FROM webhook_configs ORDER BY name"
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]