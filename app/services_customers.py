import threading
import uuid
from typing import Dict

from .core.errors import Conflict
from .schemas import CustomerWithId

# In-memory storage
_lock = threading.RLock()
_customers_by_id: Dict[str, CustomerWithId] = {}
_custid_by_email: Dict[str, str] = {}


def new_cust_id() -> str:
    with _lock:
        max_attempts = 100
        for _ in range(max_attempts):
            cust_id = f"C_{uuid.uuid4().hex[:8]}"
            if cust_id not in _customers_by_id:
                return cust_id
        raise RuntimeError(
            "Failed to generate unique customer ID after maximum attempts"
        )


def create_customer(name: str, email: str) -> CustomerWithId:
    with _lock:
        # Create instance first to apply validators (including email normalization)
        cust_id = new_cust_id()
        customer = CustomerWithId(cust_id=cust_id, name=name, email=email)
        normalized_email = customer.email
        if normalized_email in _custid_by_email:
            raise Conflict("EMAIL_DUP", "email already exists")

        _customers_by_id[cust_id] = customer
        _custid_by_email[normalized_email] = cust_id
        return customer
