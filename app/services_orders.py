import threading
import uuid
from datetime import date
from typing import Dict

from .core.errors import Conflict, NotFound
from .schemas import OrderCreate, OrderCreateResponse, OrderItemCreateResponse
from .services_customers import _customers_by_id
from .services_customers import _lock as _lock_c
from .services_products import _lock_p, _products_by_id

# In-memory storage
_lock_o = threading.RLock()
_orders_by_id: Dict[str, OrderCreateResponse] = {}
_line_no = 1


def new_order_id() -> str:
    with _lock_o:
        max_attempts = 100
        for _ in range(max_attempts):
            prod_id = f"O_{uuid.uuid4().hex[:8]}"
            if prod_id not in _orders_by_id:
                return prod_id
        raise RuntimeError("Failed to generate unique order ID after maximum attempts")


def create_order(payload: OrderCreate) -> OrderCreateResponse:
    """
    顧客・商品の存在チェックが必要
    アイテム(prodId)の重複 NG (同じ商品が複数行に出ない)
    合計金額はサーバサイドで計算
    """
    global _line_no

    with _lock_c:
        if payload.cust_id not in _customers_by_id:
            raise NotFound("CUST_NOT_FOUND", f"custId not found: {payload.cust_id}")

    seen = set()
    total = 0
    with _lock_p:
        for it in payload.items:
            if it.prod_id in seen:
                raise Conflict("ITEM_DUP", f"duplicate product line: {it.prod_id}")
            seen.add(it.prod_id)
            prod = _products_by_id.get(it.prod_id)
            if not prod:
                raise NotFound("PROD_NOT_FOUND", f"prodId not found: {it.prod_id}")
            total += prod.unit_price * it.qty

    with _lock_o:
        order_id = new_order_id()
        items = []
        for it in payload.items:
            prod = _products_by_id.get(it.prod_id)
            item = OrderItemCreateResponse(
                line_no=_line_no,
                prod_id=it.prod_id,
                qty=it.qty,
                unit_price=prod.unit_price,
                line_amount=prod.unit_price * it.qty,
            )
            items.append(item)
            _line_no += 1

        order = OrderCreateResponse(
            order_id=order_id, order_date=date.today(), total_amount=total, items=items
        )
        return order
