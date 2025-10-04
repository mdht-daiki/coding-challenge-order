def test_global_rate_limit_unauthenticated(monkeypatch):
    """認証前のグローバルレート制限を確認"""
    import importlib

    from fastapi.testclient import TestClient

    import app.main as main

    monkeypatch.setenv("TESTING", "false")
    importlib.reload(main)
    try:
        with TestClient(main.app, raise_server_exceptions=True) as client:
            for _ in range(10):
                assert client.get("/health").status_code == 200
            assert client.get("/health").status_code == 429
    finally:
        monkeypatch.setenv("TESTING", "true")
        importlib.reload(main)
