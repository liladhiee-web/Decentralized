"""
Coordinator authentication and security package.
"""

from coordinator.auth.dependencies import (
    get_api_key_or_user,
    get_current_active_user,
    get_current_user,
    require_role,
)
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

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_api_key",
    "hash_api_key",
    "generate_worker_token",
    "verify_worker_token",
    "get_current_user",
    "get_current_active_user",
    "get_api_key_or_user",
    "require_role",
]
