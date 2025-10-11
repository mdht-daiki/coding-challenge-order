import pytest

from tests.helpers import post_json


@pytest.mark.usefixtures("use_db_uow")
def test_orders_flow_on_db(client):
    ck = "test-secret"
    # 顧客・商品
    c = post_json(
        client, "/customers", {"name": "A", "email": "a@ex.com"}, api_key=ck
    ).json()
    p = post_json(
        client, "/products", {"name": "Pen", "unitPrice": 100}, api_key=ck
    ).json()
    # 注文
    r = post_json(
        client,
        "/orders",
        {"custId": c["custId"], "items": [{"prodId": p["prodId"], "qty": 2}]},
        api_key=ck,
    )
    assert r.status_code == 200
    # 検索（自分のみ）
    r2 = client.get("/orders", headers={"X-API-KEY": ck})
    assert r2.status_code == 200
    body = r2.json()
    assert body["totalCount"] >= 1
    assert body["list"][0]["totalAmount"] >= 200
