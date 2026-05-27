import os
import secrets
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "telebridge.db"
SECRET_FILE = DATA_DIR / ".secret"


def get_secret_key() -> str:
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    if SECRET_FILE.exists():
        return SECRET_FILE.read_text().strip()
    key = secrets.token_hex(32)
    SECRET_FILE.write_text(key)
    return key


SECRET_KEY = get_secret_key()
APP_URL = os.environ.get("APP_URL", "http://localhost:8000")
LOGIN_PASSWORD = os.environ.get("LOGIN_PASSWORD", "TelebridgeAa@1")
