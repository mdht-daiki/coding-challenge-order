from datetime import date
from typing import List

from app.schemas import OrderCreate, OrderItemCreate
from app.services_orders import create_order
from tests.helpers import post_json


def _mk_order_for_date(cust_id: str, prod_id: str, qty: int, ymd: str):
    from app.deps import get_uow

    payload = OrderCreate(
        cust_id=cust_id,
        items=[OrderItemCreate(prod_id=prod_id, qty=qty)],
    )

    def fixed():
        return date.fromisoformat(ymd)

    uow = get_uow()
    return create_order(uow, payload, today_provider=fixed)


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


# def test_get_orders_filter_by_custid(client):
#     api_key = "test-secret"
#     cust_ids, _ = _prepare_basic_data(client)

#     r = client.get(
#         "/orders", params={"custId": cust_ids[0]}, headers={"X-API-KEY": api_key}
#     )
#     assert r.status_code == 200
#     body = r.json()
#     assert body["totalCount"] == 3
#     assert len(body["list"]) == 3
#     item = body["list"][0]
#     assert {"orderId", "orderDate", "totalAmount"} <= set(item.keys())


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


def test_get_orders_returns_only_own_orders(client):
    """一般ユーザーは自分の注文のみ取得できることを確認"""
    # APIキー1で顧客1を作成(この時点でAPIキー1とcustId1が紐づく)
    customer1 = post_json(
        client,
        "/customers",
        {"name": "Customer 1", "email": "customer1@example.com"},
        api_key="test-api-key-1",
    ).json()

    # APIキー2で顧客2を作成(この時点でAPIキー2とcustId2が紐づく)
    customer2 = post_json(
        client,
        "/customers",
        {"name": "Customer 2", "email": "customer2@example.com"},
        api_key="test-api-key-2",
    ).json()

    # 管理者権限で商品を作成
    product = post_json(
        client,
        "/products",
        {"name": "Product A", "unitPrice": 100},
        api_key="admin-api-key",
    ).json()

    # 顧客1の注文を作成(管理者権限で作成)
    post_json(
        client,
        "/orders",
        {
            "custId": customer1["custId"],
            "items": [{"prodId": product["prodId"], "qty": 1}],
        },
        api_key="admin-api-key",
    )

    # 顧客2の注文を作成(管理者権限で作成)
    post_json(
        client,
        "/orders",
        {
            "custId": customer2["custId"],
            "items": [{"prodId": product["prodId"], "qty": 2}],
        },
        api_key="admin-api-key",
    )

    # 顧客1のAPIキーで注文を取得(自動的にcustomer1の注文のみ取得)
    response = client.get("/orders", headers={"X-API-KEY": "test-api-key-1"})

    assert response.status_code == 200
    data = response.json()
    assert data["totalCount"] == 1
    assert len(data["list"]) == 1
    assert data["list"][0]["orderId"]


def test_admin_can_get_all_orders(client):
    """管理者は全ての注文を取得できることを確認"""
    # APIキー1で顧客1を作成(この時点でAPIキー1とcustId1が紐づく)
    customer1 = post_json(
        client,
        "/customers",
        {"name": "Customer 1", "email": "customer1@example.com"},
        api_key="test-api-key-1",
    ).json()

    # APIキー2で顧客2を作成(この時点でAPIキー2とcustId2が紐づく)
    customer2 = post_json(
        client,
        "/customers",
        {"name": "Customer 2", "email": "customer2@example.com"},
        api_key="test-api-key-2",
    ).json()

    # 管理者権限で商品を作成
    product = post_json(
        client,
        "/products",
        {"name": "Product A", "unitPrice": 100},
        api_key="admin-api-key",
    ).json()

    # 顧客1の注文を作成(管理者権限で作成)
    post_json(
        client,
        "/orders",
        {
            "custId": customer1["custId"],
            "items": [{"prodId": product["prodId"], "qty": 1}],
        },
        api_key="admin-api-key",
    )

    # 顧客2の注文を作成(管理者権限で作成)
    post_json(
        client,
        "/orders",
        {
            "custId": customer2["custId"],
            "items": [{"prodId": product["prodId"], "qty": 2}],
        },
        api_key="admin-api-key",
    )

    # 顧客1のAPIキーで注文を取得(自動的にcustomer1の注文のみ取得)
    response = client.get("/orders", headers={"X-API-KEY": "admin-api-key"})

    assert response.status_code == 200
    data = response.json()
    assert data["totalCount"] == 2


def test_cannot_create_multiple_customers_with_same_api_key(client):
    """同じAPIキーで複数の顧客を作成できないことを確認"""
    # 1つ目の顧客を作成
    post_json(
        client,
        "/customers",
        {"name": "Customer 1", "email": "customer1@example.com"},
        api_key="test-api-key-1",
    )

    # 同じAPIキーで2つ目の顧客を作成しようとする
    response = post_json(
        client,
        "/customers",
        {"name": "Customer 2", "email": "customer2@example.com"},
        api_key="test-api-key-1",
    )

    assert response.status_code == 403
    assert "already associated" in response.json()["detail"]


def test_admin_can_create_multiple_customers(client):
    """管理者は複数の顧客を作成できることを確認"""
    # 管理者権限で複数の顧客を作成
    response1 = post_json(
        client,
        "/customers",
        {"name": "Customer 1", "email": "customer1@example.com"},
        api_key="admin-api-key",
    )
    response2 = post_json(
        client,
        "/customers",
        {"name": "Customer 2", "email": "customer2@example.com"},
        api_key="admin-api-key",
    )

    assert response1.status_code == 201
    assert response2.status_code == 201
