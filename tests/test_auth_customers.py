from tests.helpers import post_json


def test_customers_requires_api_key(client):
    r = client.post("/customers", json={"name": "A", "email": "a@example.com"})
    assert r.status_code == 401
    assert "X-API-KEY" in r.text


def test_customers_rejects_invalid_api_key(client):
    r = post_json(
        client, "/customers", {"name": "A", "email": "a@example.com"}, api_key="wrong"
    )
    assert r.status_code == 401
    assert "Invalid API key" in r.text


def test_customers_accepts_valid_api_key(client):
    r = post_json(
        client,
        "/customers",
        {"name": "A", "email": "a@example.com"},
        api_key="test-secret",
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "A"
