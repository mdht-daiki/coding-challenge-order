import re

from tests.helpers import post_json


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_create_customer_ok(client):
    response = post_json(
        client, "/customers", {"name": "Alice", "email": "a@example.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert re.fullmatch(r"C_[0-9a-f]{8}", body["custId"])
    assert body["name"] == "Alice"
    assert body["email"] == "a@example.com"


def test_create_product_ok(client):
    response = post_json(client, "/products", {"name": "Pen", "unitPrice": 100})
    assert response.status_code == 201
    assert "Location" in response.headers
    body = response.json()
    assert re.fullmatch(r"P_[0-9a-f]{8}", body["prodId"])
    assert body["name"] == "Pen"
    assert body["unitPrice"] == 100
