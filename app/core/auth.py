import os

from fastapi import Header, HTTPException, status

API_KEY_ENV = "API_KEY"


def get_expected_api_key() -> str:
    key = os.getenv(API_KEY_ENV)
    if not key:
        raise RuntimeError(f"Environment variable {API_KEY_ENV} is not set")
    return key


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
    if x_api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
