from tests.helpers import post_json


def test_products_requires_api_key(client):
    r = client.post("/products", json={"name": "A", "unitPrice": 1})
    assert r.status_code == 401
    assert "X-API-KEY" in r.text


def test_products_rejects_invalid_api_key(client):
    r = post_json(client, "/products", {"name": "A", "unitPrice": 1}, api_key="wrong")
    assert r.status_code == 401
    assert "Invalid API key" in r.text


def test_products_accepts_valid_api_key(client):
    r = post_json(
        client,
        "/products",
        {"name": "A", "unitPrice": 1},
        api_key="test-secret",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "A"
