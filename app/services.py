import random
import string
from typing import Dict

from .schemas import CustomerWithId

# In-memory storage
_customers_by_id: Dict[str, CustomerWithId] = {}


def new_cust_id() -> str:
    letters = string.ascii_letters + string.digits
    while True:
        cust_id = "C_" + "".join(random.choices(letters, k=8))
        if cust_id not in _customers_by_id.keys():
            return cust_id


def create_customer(name: str, email: str) -> CustomerWithId:
    if email in [v.email for v in _customers_by_id.values()]:
        from .core.errors import Conflict

        raise Conflict("EMAIL_DUP", f"email already exists: {email}")
    cust_id = new_cust_id()
    customer = CustomerWithId(custId=cust_id, name=name, email=email)
    _customers_by_id[cust_id] = customer
    return customer
