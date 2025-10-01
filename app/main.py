from fastapi import FastAPI

from .schemas import CustomerCreate, CustomerWithId
from .services import create_customer

app = FastAPI()


@app.get("/health")
async def health_check() -> dict[str, bool]:
    return {"ok": True}


@app.post("/customers", response_model=CustomerWithId)
async def post_customer(body: CustomerCreate) -> CustomerWithId:
    return create_customer(body.name, body.email)
