import re
from datetime import date

from tests.helpers import post_json


def test_create_order_ok(client):
    # 先に顧客・商品を用意
    ck = "test-secret"
    r1 = post_json(client, "/customers", {"name": "A", "email": "a@ex.com"}, api_key=ck)
    custId = r1.json()["custId"]
    p1 = post_json(
        client, "/products", {"name": "Pen", "unitPrice": 100}, api_key=ck
    ).json()
    p2 = post_json(
        client, "/products", {"name": "Note", "unitPrice": 250}, api_key=ck
    ).json()

    # 注文
    today = date.today()
    od = {
        "custId": custId,
        "items": [
            {"prodId": p1["prodId"], "qty": 2},
            {"prodId": p2["prodId"], "qty": 1},
        ],
    }
    r = post_json(client, "/orders", od, api_key=ck)
    print(r.json())
    assert r.status_code == 201
    body = r.json()
    assert re.fullmatch(r"O_[0-9a-f]{8}", body["orderId"])
    assert body["orderDate"] == today.strftime("%Y-%m-%d")
    assert body["totalAmount"] == 2 * 100 + 1 * 250
    assert isinstance(body["items"], list)


def test_create_order_missing_customer(client):
    ck = "test-secret"
    r = post_json(
        client,
        "/orders",
        {"custId": "C_404", "items": [{"prodId": "P_x", "qty": 1}]},
        api_key=ck,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "CUST_NOT_FOUND"


def test_create_order_missing_product(client):
    ck = "test-secret"
    cust = post_json(
        client, "/customers", {"name": "A", "email": "a@example.com"}, api_key=ck
    )
    r = post_json(
        client,
        "/orders",
        {"custId": cust.json()["custId"], "items": [{"prodId": "P_404", "qty": 1}]},
        api_key=ck,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "PROD_NOT_FOUND"


def test_create_order_duplicate_item(client):
    ck = "test-secret"
    cust = post_json(
        client, "/customers", {"name": "A", "email": "a@example.com"}, api_key=ck
    )
    prod = post_json(client, "/products", {"name": "Pen", "unitPrice": 100}, api_key=ck)
    payload = {
        "custId": cust.json()["custId"],
        "items": [
            {"prodId": prod.json()["prodId"], "qty": 1},
            {"prodId": prod.json()["prodId"], "qty": 2},
        ],
    }
    r = post_json(client, "/orders", payload, api_key=ck)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ITEM_DUP"


# def test_get_order(client):
#     ck = "test-secret"
#     r = client.get(
#         "/orders",
#         params={
#             "custId": "C_1234",
#             "from": date.today(),
#             "to": date.today(),
#             "page": 0,
#             "size": 20
#         },
#         headers={"X-API-KEY": ck}
#     )
#     print(r.json())


def test_create_order_sets_fixed_date(client, frozen_today):
    ck = "test-secret"
    cust = post_json(
        client, "/customers", {"name": "A", "email": "a@ex.com"}, api_key=ck
    ).json()
    prod = post_json(
        client, "/products", {"name": "Pen", "unitPrice": 100}, api_key=ck
    ).json()

    r = post_json(
        client,
        "/orders",
        {"custId": cust["custId"], "items": [{"prodId": prod["prodId"], "qty": 2}]},
        api_key=ck,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["orderDate"] == "2025-10-06"
