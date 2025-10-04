from tests.helpers import post_json


def test_ip_blocking_after_failed_attempts(client):
    """5回の認証失敗後、IPがブロックされることを確認"""
    # 5回失敗する
    for i in range(5):
        response = post_json(
            client,
            "/customers",
            {"name": f"User{i}", "email": f"user{i}@example.com"},
            api_key="invalid-key",
        )
        assert response.status_code == 401

    # 6回目は 403 Forbidden (ブロック)
    response = post_json(
        client,
        "/customers",
        {"name": "User6", "email": "user6@example.com"},
        api_key="invalid-key",
    )
    assert response.status_code == 403
    assert "Too many failed authentication attempts" in response.json()["detail"]


def test_successful_auth_resets_counter(client):
    """認証成功時に失敗カウンターがリセットされることを確認"""
    # 3回失敗
    for i in range(3):
        response = post_json(
            client,
            "/customers",
            {"name": f"User{i}", "email": f"user{i}@example.com"},
            api_key="invalid-key",
        )
        assert response.status_code == 401

    # 正しいキーで成功
    response = post_json(
        client,
        "/customers",
        {"name": "ValidUser", "email": "valid@example.com"},
        api_key="test-secret",
    )
    assert response.status_code == 201

    # 再度3回失敗してもカウントリセットによりブロックされない
    for i in range(3):
        response = post_json(
            client,
            "/customers",
            {"name": f"User{i+10}", "email": f"user{i+10}@example.com"},
            api_key="invalid-key",
        )
        assert response.status_code == 401
