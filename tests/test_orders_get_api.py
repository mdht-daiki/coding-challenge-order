from datetime import date

from app.schemas import OrderCreate, OrderItemCreate
from app.services_orders import create_order
from tests.helpers import post_json


def _mk_order_for_date(cust_id: str, prod_id: str, qty: int, ymd: str):
    payload = OrderCreate(
        cust_id=cust_id,
        items=[OrderItemCreate(prod_id=prod_id, qty=qty)],
    )

    def fixed():
        return date.fromisoformat(ymd)

    return create_order(payload, today_provider=fixed)


def _prepare_basic_data(client):
    """顧客2人、商品2つ、日付違いの注文を複数用意"""
    api_key = "test-secret"

    c1 = post_json(
        client,
        "/customers",
        {"name": "Alice", "email": "a@example.com"},
        api_key=api_key,
    ).json()
    cust_id = c1["custId"]
    c2 = post_json(
        client, "/customers", {"name": "Bob", "email": "b@example.com"}, api_key=api_key
    ).json()
    cust_id2 = c2["custId"]

    p1 = post_json(
        client, "/products", {"name": "Pen", "unitPrice": 100}, api_key=api_key
    ).json()
    p2 = post_json(
        client, "/products", {"name": "Note", "unitPrice": 250}, api_key=api_key
    ).json()

    # 受注（固定日付で3件：10/01, 10/02, 10/03）
    _mk_order_for_date(cust_id, p1["prodId"], 1, "2025-10-01")  # total=100
    _mk_order_for_date(cust_id, p2["prodId"], 2, "2025-10-02")  # total=500
    _mk_order_for_date(cust_id, p1["prodId"], 3, "2025-10-03")  # total=300
    _mk_order_for_date(cust_id2, p2["prodId"], 4, "2025-10-04")  # total=1000

    return (cust_id, cust_id2), (p1["prodId"], p2["prodId"])


def test_get_orders_requires_api_key(client):
    r = client.get("/orders")
    assert r.status_code == 401


def test_get_orders_filter_by_custid(client):
    api_key = "test-secret"
    cust_ids, _ = _prepare_basic_data(client)

    r = client.get(
        "/orders", params={"custId": cust_ids[0]}, headers={"X-API-KEY": api_key}
    )
    print(r.json())
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 3
    assert len(body["list"]) == 3
    item = body["list"][0]
    assert {"orderId", "orderDate", "totalAmount"} <= set(item.keys())
