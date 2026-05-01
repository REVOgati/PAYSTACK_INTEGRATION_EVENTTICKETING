from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()

# ── Password hashing ──────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT ───────────────────────────────────────────────────────────
ALGORITHM = "HS256"


def create_access_token(subject: str, extra_claims: dict[str, Any] = {}) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,         # subject — we'll store user id here
        "exp": expire,          # expiry timestamp
        **extra_claims,         # any extra data e.g. {"role": "organizer"}
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError:
        return {}