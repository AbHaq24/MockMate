
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from backend.config.settings import get_settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Securely hash a password before storing it."""
    if not password:
        raise ValueError("Password cannot be empty.")

    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    if not plain_password or not hashed_password:
        return False

    return password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """Create a signed JWT for an authenticated user."""
    settings = get_settings()

    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Validate a JWT and return its claims."""
    settings = get_settings()

    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured.")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired access token.") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid token subject.")

    return payload
