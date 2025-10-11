import uuid
from datetime import date
from typing import List, Optional, Tuple

from .core.errors import Conflict, NotFound
from .ports import UoW
from .schemas import (
    OrderCreate,
    OrderCreateResponse,
    OrderItemCreateResponse,
    OrderSummary,
)


def new_order_id(uow: UoW) -> str:
    max_attempts = 100
    for _ in range(max_attempts):
        order_id = f"O_{uuid.uuid4().hex[:8]}"
        if not uow.orders.exists_id(order_id):
            return order_id
    raise RuntimeError("Failed to generate unique order ID after maximum attempts")


def create_order(
    uow: UoW, payload: OrderCreate, *, today_provider=None
) -> OrderCreateResponse:
    """
    顧客・商品の存在チェックが必要
    アイテム(prodId)の重複 NG (同じ商品が複数行に出ない)
    合計金額はサーバサイドで計算
    """
    if today_provider is None:
        today_provider = date.today

    if not uow.customers.exists_id(payload.cust_id):
        raise NotFound("CUST_NOT_FOUND", f"custId not found: {payload.cust_id}")

    seen = set()
    total = 0
    for it in payload.items:
        if it.prod_id in seen:
            raise Conflict("ITEM_DUP", f"duplicate product line: {it.prod_id}")
        seen.add(it.prod_id)
        prod = uow.products.by_id(it.prod_id)
        if not prod:
            raise NotFound("PROD_NOT_FOUND", f"prodId not found: {it.prod_id}")
        total += prod.unit_price * it.qty

    order_id = new_order_id(uow)
    items = []
    for it in payload.items:
        prod = uow.products.by_id(it.prod_id)
        item = OrderItemCreateResponse(
            line_no=uow.orders.pop_line_no(),
            prod_id=it.prod_id,
            qty=it.qty,
            unit_price=prod.unit_price,
            line_amount=prod.unit_price * it.qty,
        )
        items.append(item)

    order = OrderCreateResponse(
        order_id=order_id,
        order_date=today_provider(),
        total_amount=total,
        items=items,
    )
    uow.orders.save(order, payload.cust_id)
    uow.commit()
    return order


def search_orders(
    uow: UoW,
    cust_id: Optional[str],
    from_date: Optional[date],
    to_date: Optional[date],
    page: int,
    size: int,
) -> Tuple[List[OrderSummary], int]:
    page_items, total_count = uow.orders.search(cust_id, from_date, to_date, page, size)

    summaries = [
        OrderSummary(
            order_id=o.order_id,
            order_date=o.order_date,
            total_amount=o.total_amount,
        )
        for o in page_items
    ]
    return summaries, total_count
