"""
Unit tests for cryptographic security, password hashing, and token generation.
"""

from datetime import timedelta

from coordinator.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    generate_worker_token,
    hash_api_key,
    hash_password,
    verify_password,
    verify_worker_token,
)


def test_argon2id_password_hashing() -> None:
    """Verify password hashing creates valid hash and verifies correctly."""
    pwd = "super_secure_password_123!"
    hashed = hash_password(pwd)
    assert hashed.startswith("$argon2id$")
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_access_and_refresh_tokens() -> None:
    """Verify JWT access and refresh token life-cycle and payload preservation."""
    payload = {"sub": "123e4567-e89b-12d3-a456-426614174000", "role": "user"}

    access_token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    decoded_access = decode_token(access_token)
    assert decoded_access is not None
    assert decoded_access["sub"] == payload["sub"]
    assert decoded_access["role"] == "user"
    assert decoded_access["type"] == "access"

    refresh_token = create_refresh_token(payload, expires_delta=timedelta(days=1))
    decoded_refresh = decode_token(refresh_token)
    assert decoded_refresh is not None
    assert decoded_refresh["type"] == "refresh"


def test_api_key_generation_and_hashing() -> None:
    """Verify API key formatting, entropy, and deterministic SHA-256 hashing."""
    raw_key, prefix, key_hash = generate_api_key(prefix="cld_live")
    assert raw_key.startswith("cld_live_")
    assert prefix == raw_key[:12]
    assert len(key_hash) == 64
    assert hash_api_key(raw_key) == key_hash


def test_worker_token_hmac_verification() -> None:
    """Verify HMAC token generation and comparison."""
    raw_token, token_hash = generate_worker_token()
    assert len(raw_token) > 20
    assert len(token_hash) == 64
    assert verify_worker_token(raw_token, token_hash) is True
    assert verify_worker_token("tampered_token", token_hash) is False
