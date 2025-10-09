import threading
import uuid
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from .core.errors import Conflict, NotFound
from .schemas import (
    OrderCreate,
    OrderCreateResponse,
    OrderItemCreateResponse,
    OrderSummary,
)
from .services_customers import _customers_by_id
from .services_customers import _lock as _lock_c
from .services_products import _lock_p, _products_by_id

# In-memory storage
_lock_o = threading.RLock()
_orders_by_id: Dict[str, OrderCreateResponse] = {}
_orders_by_custid: Dict[str, List[OrderCreateResponse]] = defaultdict(list)
_line_no = 1


def new_order_id() -> str:
    with _lock_o:
        max_attempts = 100
        for _ in range(max_attempts):
            prod_id = f"O_{uuid.uuid4().hex[:8]}"
            if prod_id not in _orders_by_id:
                return prod_id
        raise RuntimeError("Failed to generate unique order ID after maximum attempts")


def create_order(payload: OrderCreate, *, today_provider=None) -> OrderCreateResponse:
    """
    顧客・商品の存在チェックが必要
    アイテム(prodId)の重複 NG (同じ商品が複数行に出ない)
    合計金額はサーバサイドで計算
    """
    if today_provider is None:
        today_provider = date.today

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
            order_id=order_id,
            order_date=today_provider(),
            total_amount=total,
            items=items,
        )
        _orders_by_id[order_id] = order
        _orders_by_custid[payload.cust_id].append(order)
        return order


def search_orders(
    cust_id: Optional[str],
    from_date: Optional[date],
    to_date: Optional[date],
    page: int,
    size: int,
) -> Tuple[List[OrderSummary], int]:
    # ロック内でスナップショットをコピー
    with _lock_o:
        # orders = (
        #     list(_orders_by_custid[cust_id])
        #     if cust_id
        #     else list(_orders_by_custid.values())
        # )
        if cust_id:
            orders = list(_orders_by_custid[cust_id])
        else:
            orders = []
            for order_list in _orders_by_custid.values():
                orders.extend(order_list)

    # フィルタ
    if from_date:
        orders = [o for o in orders if o.order_date >= from_date]
    if to_date:
        orders = [o for o in orders if o.order_date <= to_date]

    # 並び順：order_date 降順
    orders.sort(key=lambda o: o.order_date, reverse=True)

    total_count = len(orders)

    # ページング
    start = page * size
    end = start + size
    page_items = orders[start:end]

    summaries = [
        OrderSummary(
            order_id=o.order_id,
            order_date=o.order_date,
            total_amount=o.total_amount,
        )
        for o in page_items
    ]
    return summaries, total_count
