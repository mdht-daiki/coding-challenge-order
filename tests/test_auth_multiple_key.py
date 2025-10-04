from tests.helpers import post_json


def test_customers_accepts_multiple_valid_api_keys(client):
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


def test_removed_key_fails_authentication(client, monkeypatch):
    """旧キーを削除した後、そのキーでの認証が失敗することを確認"""
    # 最初は両方のキーが有効
    r = post_json(
        client,
        "/customers",
        {"name": "A", "email": "a@example.com"},
        api_key="test-secret",
    )
    assert r.status_code == 201

    # 新キーに切り替え(旧キーを削除)
    monkeypatch.setenv("API_KEYS", "new-test-key")
    # アプリケーションを再初期化するか、init_api_key()を再実行
    from app.core.auth import init_api_key

    init_api_key()

    # 旧キーでの認証が失敗することを確認
    r = post_json(
        client,
        "/customers",
        {"name": "B", "email": "b@example.com"},
        api_key="test-secret",
    )
    assert r.status_code == 401

    # 新キーは引き続き動作
    r = post_json(
        client,
        "/customers",
        {"name": "C", "email": "c@example.com"},
        api_key="new-test-key",
    )
    assert r.status_code == 201
