import logging.config
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Response, status

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
            "format": "%(timestamp)s %(levelname)s %(message)s %(client_ip)s %(reason)s",
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


@app.get("/health")
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.post(
    "/customers",
    response_model=CustomerWithId,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def post_customer(body: CustomerCreate, response: Response) -> CustomerWithId:
    customer = create_customer(body.name, body.email)
    response.headers["Location"] = f"/customers/{customer.cust_id}"
    return customer


@app.post(
    "/products",
    response_model=ProductWithId,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def post_product(body: ProductCreate, response: Response) -> ProductWithId:
    product = create_product(body.name, body.unit_price)
    response.headers["Location"] = f"/products/{product.prod_id}"
    return product
