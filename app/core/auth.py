import base64
import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, Tuple

from fastapi import Header, HTTPException, Request, status

API_KEY_ENV = "API_KEY"
HASH_KEY_ENV = "API_KEY_HASH_SECRET"
logger = logging.getLogger(__name__)

# アプリケーション起動時に一度だけ検証
_EXPECTED_API_KEY: str | None = None
# Secret used for generating HMAC of API keys for logging.
_HASH_KEY: bytes | None = None

# IPアドレスごとに失敗回数と最終失敗時刻を記録
# 本番環境ではRedisなどの永続ストレージを使用推奨
_failed_attempts: Dict[str, Tuple[int, datetime]] = {}
_blocked_ips: Dict[str, datetime] = {}

MAX_FAILED_ATTEMPTS = 5  # 5回失敗でブロック
BLOCK_DURATION_MINUTES = 15  # 15分間ブロック
FAILED_ATTEMPTS_WINDOW_MINUTES = 5  # 5分以内の失敗をカウントする


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


def is_ip_blocked(client_ip: str) -> bool:
    """IPアドレスがブロックされているか確認"""
    if client_ip in _blocked_ips:
        block_until = _blocked_ips[client_ip]
        if datetime.now(timezone.utc) < block_until:
            return True
        else:
            # ブロック期間が過ぎたので解除
            del _blocked_ips[client_ip]
            if client_ip in _failed_attempts:
                del _failed_attempts[client_ip]
    return False


def record_failed_attempt(client_ip: str):
    """認証失敗を記録し、必要に応じてブロック"""
    now = datetime.now(timezone.utc)

    if client_ip in _failed_attempts:
        count, last_attempt = _failed_attempts[client_ip]
        # 時間窓内の失敗ならカウントを増やす
        if now - last_attempt < timedelta(minutes=FAILED_ATTEMPTS_WINDOW_MINUTES):
            count += 1
        else:
            # 時間窓を過ぎたのでリセット
            count = 1
    else:
        count = 1

    _failed_attempts[client_ip] = (count, now)

    # 閾値を超えたらブロック
    if count >= MAX_FAILED_ATTEMPTS:
        block_until = now + timedelta(minutes=BLOCK_DURATION_MINUTES)
        _blocked_ips[client_ip] = block_until
        logger.warning(
            "IP blocked due to excessive failed attempts",
            extra={
                "client_ip": client_ip,
                "failed_attempts": count,
                "block_until": block_until.isoformat(),
            },
        )


def reset_failed_attempts(client_ip: str):
    """認証成功時に失敗カウントをリセット"""
    if client_ip in _failed_attempts:
        del _failed_attempts[client_ip]


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-KEY"),
):
    """
    認可用の依存関数 + 監査ログ + IPブロック
    - ヘッダ未指定 or 不一致 -> 401
    """
    client_ip = request.client.host if request and request.client else "unknown"

    # IPブロックチェック
    if is_ip_blocked(client_ip):
        logger.warning(
            "Blocked IT attempted access",
            extra={
                "client_ip": client_ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "ip_blocked",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Too many failed authentication attempts. Please try again later.",
        )

    expected = get_expected_api_key()

    if not x_api_key:
        record_failed_attempt(client_ip)
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
        record_failed_attempt(client_ip)
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
    reset_failed_attempts(client_ip)
    logger.info(
        "Authentication successful",
        extra={
            "client_ip": client_ip,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "key_hash": key_hash,
            "result": "success",
        },
    )
