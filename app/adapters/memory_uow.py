import threading
from collections import defaultdict
from datetime import date
from typing import Dict, List

from ..ports import CustomersRepo, OrdersRepo, ProductsRepo, UoW
from ..schemas import CustomerWithId, OrderCreateResponse, ProductWithId


class _CustomersMem(CustomersRepo):
    def __init__(self):
        self._by_id: Dict[str, CustomerWithId] = {}
        self._by_email: Dict[str, str] = {}
        self._lock = threading.RLock()

    def by_id(self, cust_id: str) -> CustomerWithId | None:
        with self._lock:
            return self._by_id.get(cust_id)

    def exists_id(self, cust_id: str) -> bool:
        with self._lock:
            return cust_id in self._by_id

    def exists_email(self, email: str) -> bool:
        with self._lock:
            return email.lower() in self._by_email

    def save(self, c: CustomerWithId) -> None:
        with self._lock:
            self._by_id[c.cust_id] = c
            self._by_email[c.email.lower()] = c.cust_id


class _ProductsMem(ProductsRepo):
    def __init__(self):
        self._by_id: Dict[str, ProductWithId] = {}
        self._by_name: Dict[str, str] = {}
        self._lock = threading.RLock()

    def by_id(self, prod_id: str) -> ProductWithId | None:
        with self._lock:
            return self._by_id.get(prod_id)

    def by_name_norm_exists(self, name_norm: str) -> bool:
        with self._lock:
            return name_norm in self._by_name

    def save(self, p: ProductWithId) -> None:
        with self._lock:
            self._by_id[p.prod_id] = p
            self._by_name[p.name.strip().lower()] = p.prod_id

    def exists_id(self, prod_id: str) -> bool:
        with self._lock:
            return prod_id in self._by_id


class _OrdersMem(OrdersRepo):
    def __init__(self):
        self._by_id: Dict[str, OrderCreateResponse] = {}
        self._by_custid: Dict[str, List[OrderCreateResponse]] = defaultdict(list)
        self._lock = threading.RLock()

    def by_id(self, order_id: str) -> OrderCreateResponse | None:
        with self._lock:
            return self._by_id.get(order_id)

    def save(self, o: OrderCreateResponse, cust_id: str) -> None:
        with self._lock:
            self._by_id[o.order_id] = o
            self._by_custid[cust_id].append(o)

    def exists_id(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._by_id

    def search(
        self,
        cust_id: str | None,
        frm: date | None,
        to: date | None,
        page: int,
        size: int,
    ) -> tuple[list[OrderCreateResponse], int]:
        with self._lock:
            if cust_id:
                values = list(self._by_custid[cust_id])
            else:
                values = []
                for value in self._by_custid.values():
                    values.extend(value)

        if frm:
            values = [o for o in values if o.order_date >= frm]
        if to:
            values = [o for o in values if o.order_date <= to]

        values.sort(key=lambda o: o.order_date, reverse=True)

        total = len(values)

        start = page * size
        end = start + size
        page_items = values[start:end]

        return page_items, total


class MemoryUoW(UoW):
    def __init__(self):
        self.customers = _CustomersMem()
        self.products = _ProductsMem()
        self.orders = _OrdersMem()

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass
