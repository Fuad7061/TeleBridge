import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import SECRET_KEY


def _derive_fernet_key() -> bytes:
    raw = hashlib.sha256(SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt(plaintext: str) -> str:
    f = Fernet(_derive_fernet_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    f = Fernet(_derive_fernet_key())
    return f.decrypt(ciphertext.encode()).decode()
