from fastapi import FastAPI

from .schemas import CustomerCreate, CustomerWithId, ProductCreate, ProductWithId
from .services import create_customer
from .services_products import create_product

app = FastAPI()


@app.get("/health")
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.post("/customers", response_model=CustomerWithId)
async def post_customer(body: CustomerCreate) -> CustomerWithId:
    return create_customer(body.name, body.email)


@app.post("/products", response_model=ProductWithId)
async def post_product(body: ProductCreate) -> ProductWithId:
    return create_product(body.name, body.unit_price)
