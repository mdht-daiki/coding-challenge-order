import threading
import uuid
from typing import Dict

from .core.errors import Conflict
from .ports import UoW
from .schemas import CustomerWithId

# In-memory storage
_lock = threading.RLock()
_customers_by_id: Dict[str, CustomerWithId] = {}
_custid_by_email: Dict[str, str] = {}


def new_cust_id(uow: UoW) -> str:
    max_attempts = 100
    for _ in range(max_attempts):
        cust_id = f"C_{uuid.uuid4().hex[:8]}"
        if not uow.customers.exists_id(cust_id):
            return cust_id
    raise RuntimeError("Failed to generate unique customer ID after maximum attempts")


def create_customer(uow: UoW, name: str, email: str) -> CustomerWithId:
    # Create instance first to apply validators (including email normalization)
    cust_id = new_cust_id(uow)
    customer = CustomerWithId(cust_id=cust_id, name=name, email=email)
    if uow.customers.exists_email(customer.email):
        raise Conflict("EMAIL_DUP", "email already exists")

    uow.customers.save(customer)
    uow.commit()
    return customer
