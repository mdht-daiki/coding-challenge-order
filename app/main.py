import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request as StarletteRequest

from .core.auth import init_api_key, require_api_key
from .core.exception_handlers import include_handlers
from .schemas import CustomerCreate, CustomerWithId, ProductCreate, ProductWithId
from .services import create_customer
from .services_products import create_product

# テスト環境かどうかを判定
TESTING = os.getenv("TESTING", "false").lower() == "true"

# グローバルレート制限
GLOBAL_RATE_LIMIT = "100/minute" if TESTING else "10/minute"
# 認証済みエンドポイント用
AUTH_RATE_LIMIT = "10000/minute" if TESTING else "5/minute"


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "auth_audit.log",
            "formatter": "json",
        }
    },
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(timestamp)s %(levelname)s %(message)s %(client_ip)s %(result)s %(key_hash)s %(reason)s",
        }
    },
    "loggers": {"app.core.auth": {"handlers": ["file"], "level": "INFO"}},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # スタートアップ処理
    logging.config.dictConfig(LOGGING_CONFIG)
    init_api_key()
    yield
    # シャットダウン処理（必要に応じて追加）


def get_api_key_for_limit(request: Request) -> str:
    """レート制限用にAPIキーを抽出する（認証済みエンドポイント専用）"""
    # X-API-KEY ヘッダーからキーを取得
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        # Authorization ヘッダーからも実行
        auth_header = request.headers.get("Authorization", "")
        api_key = (
            auth_header.replace("Bearer ", "")
            if auth_header.startswith("Bearer ")
            else auth_header
        )
    return api_key or "unknown"


# Limiterの初期化（default_limitsでグローバル制限を設定）
limiter = Limiter(
    key_func=get_api_key_for_limit,
    default_limits=[GLOBAL_RATE_LIMIT],  # ← グローバル制限
    headers_enabled=True,  # X-RateLimit-* ヘッダーを有効化
)

app = FastAPI(title="Order Management API", version="1.0.0", lifespan=lifespan)

include_handlers(app)

# Limiterをアプリケーションにバインド
app.state.limiter = limiter

# SlowAPIMiddlewareを追加（これが自動的にレート制限をチェック）
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: StarletteRequest, exc: RateLimitExceeded):
    """
    レート制限超過時のカスタムエラーハンドラー
    既存のエラーレスポンス形式 {"code", "message", "details"} に統一
    """
    # SlowAPI のヘッダー情報を取得（利用可能な場合）
    headers = {}
    if hasattr(exc, "headers") and exc.headers:
        headers = exc.headers

    # 詳細情報を構築
    details = {
        "limit": str(exc.detail) if hasattr(exc, "detail") else "制限に達しました"
    }

    # X-RateLimit-* ヘッダーから情報を抽出
    if "X-RateLimit-Limit" in headers:
        details["rate_limit"] = headers["X-RateLimit-Limit"]
    if "X-RateLimit-Remaining" in headers:
        details["remaining"] = headers["X-RateLimit-Remaining"]
    if "X-RateLimit-Reset" in headers:
        details["reset_at"] = headers["X-RateLimit-Reset"]

    return JSONResponse(
        status_code=429,
        content={
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "リクエスト数が制限を超えました。しばらくしてから再試行してください。",
            "details": details,
        },
        headers=headers,  # レート制限情報をヘッダーにも含める
    )


@app.get("/health")
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.post(
    "/customers",
    response_model=CustomerWithId,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(AUTH_RATE_LIMIT)
async def post_customer(
    request: Request,  # slowapi のレート制限に必要
    body: CustomerCreate,
    response: Response,
) -> CustomerWithId:
    customer = create_customer(body.name, body.email)
    response.headers["Location"] = f"/customers/{customer.cust_id}"
    return customer


@app.post(
    "/products",
    response_model=ProductWithId,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(AUTH_RATE_LIMIT)
async def post_product(
    request: Request,  # slowapi のレート制限に必要
    body: ProductCreate,
    response: Response,
) -> ProductWithId:
    product = create_product(body.name, body.unit_price)
    response.headers["Location"] = f"/products/{product.prod_id}"
    return product
