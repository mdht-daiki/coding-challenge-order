# tests/conftest.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def set_api_key_env(monkeypatch):
    # テスト専用固定キー
    monkeypatch.setenv("API_KEY", "test-secret")
    yield


@pytest.fixture
def client():
    from app.main import app  # ← ここでだけ import

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_storage():
    """各テストの前後でインメモリストレージを確実にクリア"""
    from app.services import _custid_by_email, _customers_by_id, _lock
    from app.services_products import _lock_p, _prodid_by_name, _products_by_id

    with _lock:
        _customers_by_id.clear()
        _custid_by_email.clear()
    with _lock_p:
        _products_by_id.clear()
        _prodid_by_name.clear()
    try:
        yield
    finally:
        with _lock:
            _customers_by_id.clear()
            _custid_by_email.clear()
        with _lock_p:
            _products_by_id.clear()
            _prodid_by_name.clear()
