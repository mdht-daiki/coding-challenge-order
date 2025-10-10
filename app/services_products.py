import uuid

from .core.errors import Conflict
from .ports import UoW
from .schemas import ProductWithId


def new_prod_id(uow: UoW) -> str:
    max_attempts = 100
    for _ in range(max_attempts):
        prod_id = f"P_{uuid.uuid4().hex[:8]}"
        if not uow.products.exists_id(prod_id):
            return prod_id
    raise RuntimeError("Failed to generate unique product ID after maximum attempts")


def create_product(uow: UoW, name: str, unit_price) -> ProductWithId:
    name_lower = name.strip().lower()
    if uow.products.by_name_norm_exists(name_lower):
        raise Conflict("NAME_DUP", "name already exists")
    prod_id = new_prod_id(uow)
    product = ProductWithId(prod_id=prod_id, name=name, unit_price=unit_price)

    uow.products.save(product)
    uow.commit()
    return product
