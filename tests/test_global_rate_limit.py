def test_global_rate_limit_unauthenticated(client_with_rate_limit):
    """認証前のグローバルレート制限を確認"""
    for i in range(10):
        response = client_with_rate_limit.get("/health")
        assert response.status_code == 200, f"Request {i+1} should succeed"

    # 11回目はグローバルレート制限超過で429エラー
    response = client_with_rate_limit.get("/health")

    assert response.status_code == 429
    data = response.json()

    assert "code" in data
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert "message" in data
    assert "details" in data
    assert isinstance(data["details"], dict)


def test_auth_rate_limit_response_format(client_with_rate_limit):
    """認証エンドポイントのレート制限エラーが既存のエラー形式に従うことを確認"""
    # /customersエンドポイントにAUTH_RATE_LIMIT（5/minute）まで連続リクエスト
    for i in range(5):
        response = client_with_rate_limit.post(
            "/customers",
            json={"name": f"User{i}", "email": f"user{i}@example.com"},
            headers={"X-API-KEY": "test-secret"},
        )
        assert response.status_code == 201, f"Request {i+1} should succeed"

    # 6回目はAUTH_RATE_LIMIT超過で429エラー
    response = client_with_rate_limit.post(
        "/customers",
        json={"name": "User6", "email": "user6@example.com"},
        headers={"X-API-KEY": "test-secret"},
    )

    assert response.status_code == 429
    data = response.json()

    # 既存のエラー形式に従っているか確認
    assert "code" in data
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert "message" in data
    assert "details" in data
    assert isinstance(data["details"], dict)
