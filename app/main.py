import logging.config
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request as StarletteRequest

from .core.auth import (
    bind_api_key_to_customer,
    get_customer_id_from_api_key,
    init_api_key,
    initialize_api_keys,
    is_admin_api_key,
    is_api_key_bound,
    is_valid_api_key,
    require_api_key,
)
from .core.exception_handlers import include_handlers
from .deps import get_uow
from .ports import UoW
from .schemas import (
    AuthContext,
    CustomerCreate,
    CustomerWithId,
    OrderCreate,
    OrderCreateResponse,
    ProductCreate,
    ProductWithId,
)
from .services_customers import create_customer
from .services_orders import create_order, search_orders
from .services_products import create_product

# テスト環境かどうかを判定
TESTING = os.getenv("TESTING", "false").lower() == "true"

# グローバルレート制限
GLOBAL_RATE_LIMIT = "100/minute" if TESTING else "10/minute"
# 認証済みエンドポイント用
AUTH_RATE_LIMIT = "10000/minute" if TESTING else "5/minute"

# Redis接続情報を環境変数から取得（本番環境用）
REDIS_URL = os.getenv("REDIS_URL", "")


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
    initialize_api_keys()
    yield
    # シャットダウン処理（必要に応じて追加）


def get_api_key_for_limit(request: Request) -> str:
    """レート制限用にAPIキーを抽出する（認証済みエンドポイント専用）"""
    # X-API-KEY ヘッダーからキーを取得
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        # Authorization ヘッダーからも取得
        auth_header = request.headers.get("Authorization", "")
        api_key = (
            auth_header.replace("Bearer ", "")
            if auth_header.startswith("Bearer ")
            else auth_header
        )
    return api_key if api_key else get_remote_address(request)


async def get_auth_context(request: Request) -> AuthContext:
    """認証コンテキストを取得"""
    api_key = request.headers.get("X-API-KEY")
    if not api_key or not is_valid_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    customer_id = get_customer_id_from_api_key(api_key)
    is_admin = is_admin_api_key(api_key)

    return AuthContext(api_key=api_key, customer_id=customer_id, is_admin=is_admin)


# Limiterの初期化（default_limitsでグローバル制限を設定）
limiter = Limiter(
    key_func=get_api_key_for_limit,
    default_limits=[GLOBAL_RATE_LIMIT],  # ← グローバル制限
    headers_enabled=True,  # X-RateLimit-* ヘッダーを有効化
    storage_uri=REDIS_URL if REDIS_URL else None,  # 本番環境ではRedisを使用
)

app = FastAPI(title="Order Management API", version="1.0.0", lifespan=lifespan)


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
            "message": "Rate limit exceeded. Please try again later.",
            "details": details,
        },
        headers=headers,  # レート制限情報をヘッダーにも含める
    )


include_handlers(app)

# Limiterをアプリケーションにバインド
app.state.limiter = limiter


@app.get("/health")
@limiter.limit(GLOBAL_RATE_LIMIT)
async def health_check(request: Request, response: Response) -> dict[str, bool]:
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
    uow: UoW = Depends(get_uow),
) -> CustomerWithId:
    """
    顧客を作成
    - 管理者: 制限なく作成可能
    - 一般ユーザー: 1つのAPIキーにつき1顧客まで作成可能
    """
    api_key = request.headers.get("X-API-KEY")

    # 管理者でない場合、すでにバインド済みならエラー
    if not is_admin_api_key(api_key) and is_api_key_bound(api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key is already associated with a customer",
        )

    customer = create_customer(uow, body.name, body.email)
    response.headers["Location"] = f"/customers/{customer.cust_id}"

    # APIキーを顧客IDにバインド(管理者キーの場合は何もしない)
    bind_api_key_to_customer(api_key, customer.cust_id)
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
    uow: UoW = Depends(get_uow),
) -> ProductWithId:
    product = create_product(uow, body.name, body.unit_price)
    response.headers["Location"] = f"/products/{product.prod_id}"
    return product


@app.post(
    "/orders",
    response_model=OrderCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(AUTH_RATE_LIMIT)
async def post_order(
    request: Request,  # slowapi のレート制限に必要
    body: OrderCreate,
    response: Response,
    uow: UoW = Depends(get_uow),
) -> OrderCreateResponse:
    order = create_order(uow, body)
    response.headers["Location"] = f"/orders/{order.order_id}"
    return order


@app.get(
    "/orders", status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_key)]
)
@limiter.limit(AUTH_RATE_LIMIT)
async def get_order(
    request: Request,
    response: Response,
    auth_context: AuthContext = Depends(get_auth_context),
    from_date: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = None,
    page: Optional[int] = 0,
    size: Optional[int] = 20,
    uow: UoW = Depends(get_uow),
):
    """
    注文一覧を取得
    - 一般ユーザー：自分の注文のみ取得
    - 管理者：すべての注文を取得
    """
    cust_id = None if auth_context.is_admin else auth_context.customer_id

    if not auth_context.is_admin and auth_context.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No customer associated with this API key",
        )

    items, total_count = search_orders(uow, cust_id, from_date, to, page, size)
    return {
        "list": [i.model_dump(by_alias=True) for i in items],
        "totalCount": total_count,
        "page": page,
        "size": size,
    }
