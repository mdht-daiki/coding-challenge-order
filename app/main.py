import logging.config
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .core.auth import init_api_key, require_api_key
from .core.exception_handlers import include_handlers
from .schemas import CustomerCreate, CustomerWithId, ProductCreate, ProductWithId
from .services import create_customer
from .services_products import create_product

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


app = FastAPI(lifespan=lifespan)

include_handlers(app)

limiter = Limiter(key_func=get_remote_address)
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
@limiter.limit("5/minute")  # 1分間に5回まで
async def post_customer(
    request: Request, body: CustomerCreate, response: Response
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
@limiter.limit("5/minute")  # 1分間に5回まで
async def post_product(
    request: Request, body: ProductCreate, response: Response
) -> ProductWithId:
    product = create_product(body.name, body.unit_price)
    response.headers["Location"] = f"/products/{product.prod_id}"
    return product
