from tests.helpers import post_json


def test_customers_accepts_multiple_valid_api_key(client):
    r = post_json(
        client,
        "/customers",
        {"name": "A", "email": "a@example.com"},
        api_key="test-secret",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "A"

    r = post_json(
        client,
        "/customers",
        {"name": "B", "email": "b@example.com"},
        api_key="new-test-key",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "B"
