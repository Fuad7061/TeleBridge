import secrets
import time

from fastapi import Request, HTTPException
from starlette.responses import RedirectResponse

from app.config import LOGIN_PASSWORD

_sessions: dict[str, float] = {}
SESSION_TTL = 86400 * 7
COOKIE_NAME = "tb_session"


def create_session() -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_TTL
    return token


def validate_session(token: str | None) -> bool:
    if not token:
        return False
    expiry = _sessions.get(token)
    if not expiry:
        return False
    if time.time() > expiry:
        del _sessions[token]
        return False
    return True


def delete_session(token: str):
    _sessions.pop(token, None)


def get_session_token(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


def require_auth(request: Request):
    token = get_session_token(request)
    if not validate_session(token):
        raise HTTPException(status_code=401, detail="Unauthorized")


def check_password(password: str) -> bool:
    return password == LOGIN_PASSWORD
