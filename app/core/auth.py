import os
import secrets

from fastapi import Header, HTTPException, status

API_KEY_ENV = "API_KEY"

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
    x_api_key: str | None = Header(default=None, alias="X-API-KEY")
):
    """
    認可用の依存関数
    - ヘッダ未指定 or 不一致 -> 401
    """
    expected = get_expected_api_key()
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-KEY header required",
        )
    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
