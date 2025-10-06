from datetime import date
from typing import List

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
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 3
    assert len(body["list"]) == 3
    item = body["list"][0]
    assert {"orderId", "orderDate", "totalAmount"} <= set(item.keys())


def test_get_orders_filter_from(client):
    api_key = "test-secret"
    _prepare_basic_data(client)

    r = client.get(
        "/orders",
        params={"from": date.fromisoformat("2025-10-02")},
        headers={"X-API-KEY": api_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 3
    dates: List[str] = [it["orderDate"] for it in body["list"]]
    assert set(dates) == {"2025-10-02", "2025-10-03", "2025-10-04"}


def test_get_orders_filter_to(client):
    api_key = "test-secret"
    _prepare_basic_data(client)

    r = client.get(
        "/orders",
        params={"to": date.fromisoformat("2025-10-02")},
        headers={"X-API-KEY": api_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 2
    dates: List[str] = [it["orderDate"] for it in body["list"]]
    assert set(dates) == {"2025-10-01", "2025-10-02"}


def test_get_orders_filter_from_to(client):
    api_key = "test-secret"
    _prepare_basic_data(client)

    r = client.get(
        "/orders",
        params={
            "from": date.fromisoformat("2025-10-02"),
            "to": date.fromisoformat("2025-10-02"),
        },
        headers={"X-API-KEY": api_key},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["totalCount"] == 1
    assert len(body["list"]) == 1
    assert body["list"][0]["orderDate"] == "2025-10-02"


def test_get_orders_pagination(client):
    api_key = "test-secret"
    _prepare_basic_data(client)

    r0 = client.get(
        "/orders", params={"page": 0, "size": 1}, headers={"X-API-KEY": api_key}
    ).json()
    r1 = client.get(
        "/orders", params={"page": 1, "size": 1}, headers={"X-API-KEY": api_key}
    ).json()
    r2 = client.get(
        "/orders", params={"page": 2, "size": 1}, headers={"X-API-KEY": api_key}
    ).json()
    r3 = client.get(
        "/orders", params={"page": 3, "size": 1}, headers={"X-API-KEY": api_key}
    ).json()

    assert (
        r0["totalCount"]
        == r1["totalCount"]
        == r2["totalCount"]
        == r3["totalCount"]
        == 4
    )
    assert len(r0["list"]) == len(r1["list"]) == len(r2["list"]) == len(r3["list"]) == 1
    assert r0["list"][0]["orderDate"] == "2025-10-04"
    assert r1["list"][0]["orderDate"] == "2025-10-03"
    assert r2["list"][0]["orderDate"] == "2025-10-02"
    assert r3["list"][0]["orderDate"] == "2025-10-01"


def test_get_orders_sorted_desc_by_default(client):
    api_key = "test-secret"
    _prepare_basic_data(client)

    r = client.get("/orders", headers={"X-API-KEY": api_key})
    assert r.status_code == 200
    dates: List[str] = [it["orderDate"] for it in r.json()["list"]]
    assert dates == sorted(dates, reverse=True)
