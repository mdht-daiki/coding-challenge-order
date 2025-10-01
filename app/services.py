import random
import string
import threading
from typing import Dict

from .core.errors import Conflict
from .schemas import CustomerWithId

# In-memory storage
_lock = threading.Lock()
_customers_by_id: Dict[str, CustomerWithId] = {}
_custid_by_email: Dict[str, str] = {}


def new_cust_id() -> str:
    letters = string.ascii_letters + string.digits
    max_attempts = 100
    for _ in range(max_attempts):
        cust_id = "C_" + "".join(random.choices(letters, k=8))
        if cust_id not in _customers_by_id:
            return cust_id
    raise RuntimeError("Failed to generate unique customer ID after maximum attempts")


def create_customer(name: str, email: str) -> CustomerWithId:
    with _lock:
        if email in _custid_by_email:
            raise Conflict("EMAIL_DUP", f"email already exists: {email}")

        cust_id = new_cust_id()
        customer = CustomerWithId(cust_id=cust_id, name=name, email=email)
        _customers_by_id[cust_id] = customer
        _custid_by_email[email] = cust_id
        return customer
