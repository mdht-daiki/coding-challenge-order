import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Header, HTTPException, Request, status

API_KEY_ENV = "API_KEY"
HASH_KEY_ENV = "API_KEY_HASH_SECRET"
logger = logging.getLogger(__name__)

# アプリケーション起動時に一度だけ検証
_EXPECTED_API_KEY: str | None = None
# Secret used for generating HMAC of API keys for logging.
_HASH_KEY: bytes | None = None


def init_api_key():
    """起動時に呼び出してAPI_KEYを検証・キャッシュ"""
    global _EXPECTED_API_KEY, _HASH_KEY
    _EXPECTED_API_KEY = os.getenv(API_KEY_ENV)
    if not _EXPECTED_API_KEY:
        raise RuntimeError(f"Environment variable {API_KEY_ENV} is not set")
    hash_secret = os.getenv(HASH_KEY_ENV)
    if not hash_secret:
        raise RuntimeError(f"Environment variable {HASH_KEY_ENV} is not set")
    _HASH_KEY = hash_secret.encode()


def _get_hash_key() -> bytes:
    if _HASH_KEY is None:
        raise RuntimeError("API key hash secret is not initialized")
    return _HASH_KEY


def get_expected_api_key() -> str:
    if _EXPECTED_API_KEY is None:
        raise RuntimeError(f"Environment variable {API_KEY_ENV} is not set")
    return _EXPECTED_API_KEY


@lru_cache(maxsize=128)
def _compute_key_hash(key: str) -> str:
    """
    監査ログ用のAPI キー識別子を生成(HMAC-SHA256)

    Note: This is NOT for password storage. HMAC-SHA256 is appropriate for
    generating stable, non-reversible identifiers for audit logging.
    CodeQL may flag this, but it's a false positive for this use case.
    """
    # codeql[py/weak-cryptographic-algorithm]
    mac = hmac.new(_get_hash_key(), key.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode("utf-8")[:16]


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-KEY"),
):
    """
    認可用の依存関数 + 監査ログ
    - ヘッダ未指定 or 不一致 -> 401
    """
    client_ip = request.client.host if request and request.client else "unknown"
    expected = get_expected_api_key()

    if not x_api_key:
        logger.warning(
            "Authentication failed - missing API key",
            extra={
                "client_ip": client_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "missing_header",
                "result": "failure",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header required",
        )

    key_hash = _compute_key_hash(x_api_key)

    if not secrets.compare_digest(x_api_key, expected):
        logger.warning(
            "Authentication failed - invalid API key",
            extra={
                "client_ip": client_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "invalid_key",
                "key_hash": key_hash,
                "result": "failure",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # 成功ログ
    logger.info(
        "Authentication successful",
        extra={
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key_hash": key_hash,
            "result": "success",
        },
    )
