import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone

from fastapi import Header, HTTPException, Request, status

API_KEY_ENV = "API_KEY"
logger = logging.getLogger(__name__)

# アプリケーション起動時に一度だけ検証
_EXPECTED_API_KEY: str | None = None


def init_api_key():
    """起動時に呼び出してAPI_KEYを検証・キャッシュ"""
    global _EXPECTED_API_KEY
    _EXPECTED_API_KEY = os.getenv(API_KEY_ENV)
    if not _EXPECTED_API_KEY:
        raise RuntimeError(f"Environment variable {API_KEY_ENV} is not set")


def get_expected_api_key() -> str:
    if _EXPECTED_API_KEY is None:
        raise RuntimeError(f"Environment variable {API_KEY_ENV} is not set")
    return _EXPECTED_API_KEY


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

    # API キーのハッシュ値を識別子として使用
    def get_key_hash(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]  # 最初の16文字

    if not x_api_key:
        logger.warning(
            "Authentication failed - missing API key",
            extra={
                "client_ip": client_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "missing_header",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header required",
        )

    key_hash = get_key_hash(x_api_key)

    if not secrets.compare_digest(x_api_key, expected):
        logger.warning(
            "Authentication failed - invalid API key",
            extra={
                "client_ip": client_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "invalid_key",
                "key_hash": key_hash,
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
        },
    )
