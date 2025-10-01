def test_create_customer_ok(client):
    response = client.post(
        "/customers", json={"name": "Alice", "email": "a@example.com"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["custId"].startswith("C_")
    assert body["name"] == "Alice"
    assert body["email"] == "a@example.com"
