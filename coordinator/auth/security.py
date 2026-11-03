"""
Cryptographic security utilities for authentication, password hashing, and token generation.
Implements Argon2id password hashing, JWT bearer tokens, API keys, and worker secrets.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from coordinator.config import get_settings

settings = get_settings()

# Initialize Argon2id password hasher with production parameters
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, Exception):
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a short-lived signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a longer-lived signed JWT refresh token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and cryptographically verify a JWT token."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.PyJWTError, Exception):
        return None


def generate_api_key(prefix: str = "cld_live") -> tuple[str, str, str]:
    """
    Generate a high-entropy API key for automated and CLI access.
    Returns: (raw_key, key_prefix, key_hash)
    """
    random_part = secrets.token_hex(24)
    raw_key = f"{prefix}_{random_part}"
    key_prefix = raw_key[:12]
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, key_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256 for secure database storage and lookup."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_worker_token() -> tuple[str, str]:
    """
    Generate a high-entropy registration token for a worker compute node.
    Returns: (raw_token, token_hash)
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hmac.new(
        settings.WORKER_AUTH_TOKEN_SALT.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return raw_token, token_hash


def verify_worker_token(raw_token: str, token_hash: str) -> bool:
    """Verify an incoming worker secret token against the stored HMAC hash."""
    computed_hash = hmac.new(
        settings.WORKER_AUTH_TOKEN_SALT.encode("utf-8"),
        raw_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed_hash, token_hash)
