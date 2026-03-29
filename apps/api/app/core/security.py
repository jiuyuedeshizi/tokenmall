import hashlib
import hmac
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire_at}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def generate_api_key() -> tuple[str, str, str]:
    raw_value = f"tk_live_{secrets.token_urlsafe(24)}"
    digest = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()
    return raw_value, raw_value[:12], digest


def hash_api_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _api_key_cipher_key() -> bytes:
    return hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()


def encrypt_api_key(value: str) -> str:
    payload = value.encode("utf-8")
    key = _api_key_cipher_key()
    nonce = secrets.token_bytes(16)
    keystream = bytearray()
    counter = 0

    while len(keystream) < len(payload):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        keystream.extend(block)
        counter += 1

    cipher = bytes(payload[index] ^ keystream[index] for index in range(len(payload)))
    signature = hmac.new(key, nonce + cipher, hashlib.sha256).digest()
    return urlsafe_b64encode(nonce + cipher + signature).decode("utf-8")


def decrypt_api_key(value: str) -> str:
    raw = urlsafe_b64decode(value.encode("utf-8"))
    nonce = raw[:16]
    signature = raw[-32:]
    cipher = raw[16:-32]
    key = _api_key_cipher_key()
    expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()

    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid encrypted api key")

    keystream = bytearray()
    counter = 0
    while len(keystream) < len(cipher):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        keystream.extend(block)
        counter += 1

    payload = bytes(cipher[index] ^ keystream[index] for index in range(len(cipher)))
    return payload.decode("utf-8")
