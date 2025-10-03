import threading
import uuid
from typing import Dict

from .core.errors import Conflict
from .schemas import ProductWithId

# In-memory storage
_lock_p = threading.RLock()
_products_by_id: Dict[str, ProductWithId] = {}
_prodid_by_name: Dict[str, str] = {}


def new_prod_id() -> str:
    with _lock_p:
        max_attempts = 100
        for _ in range(max_attempts):
            prod_id = f"P_{uuid.uuid4().hex[:8]}"
            if prod_id not in _products_by_id:
                return prod_id
        raise RuntimeError(
            "Failed to generate unique product ID after maximum attempts"
        )


def create_product(name: str, unit_price) -> ProductWithId:
    with _lock_p:
        name_lower = name.strip().lower()
        if name_lower in _prodid_by_name:
            raise Conflict("NAME_DUP", "name already exists")
        prod_id = new_prod_id()
        product = ProductWithId(prod_id=prod_id, name=name, unit_price=unit_price)

        _products_by_id[prod_id] = product
        _prodid_by_name[name_lower] = prod_id
        return product
