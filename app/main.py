import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.auth import init_api_key, require_api_key
from .core.exception_handlers import include_handlers
from .schemas import CustomerCreate, CustomerWithId, ProductCreate, ProductWithId
from .services import create_customer
from .services_products import create_product

# テスト環境かどうかを判定
TESTING = os.getenv("TESTING", "false").lower() == "true"

# レート制限の設定（テスト環境では無効化）
if TESTING:
    # テスト環境では実質的に無制限
    RATE_LIMIT = "10000/minute"
else:
    # 本番環境では5回/分
    RATE_LIMIT = "5/minute"


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


app = FastAPI(lifespan=lifespan)

include_handlers(app)

limiter = Limiter(key_func=get_api_key_for_limit)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.post(
    "/customers",
    response_model=CustomerWithId,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(RATE_LIMIT)
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
@limiter.limit(RATE_LIMIT)
async def post_product(
    request: Request,  # slowapi のレート制限に必要
    body: ProductCreate,
    response: Response,
) -> ProductWithId:
    product = create_product(body.name, body.unit_price)
    response.headers["Location"] = f"/products/{product.prod_id}"
    return product
