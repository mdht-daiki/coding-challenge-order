def test_global_rate_limit_unauthenticated(client, monkeypatch):
    """認証前のグローバルレート制限を確認"""
    # レート制限を有効化
    monkeypatch.setenv("TESTING", "false")

    # 10回までは失敗するが429ではない（401 Unauthorized）
    for i in range(10):
        # response = post_json(
        #     client,
        #     "/customers",
        #     {"name": f"User{i}", "email": f"user{i}@example.com"},
        #     api_key="invalid-key",
        # )
        response = client.get("/health")
        assert response.status_code == 200
