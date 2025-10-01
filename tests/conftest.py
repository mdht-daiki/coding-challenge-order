# tests/conftest.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app  # ← ここでだけ import

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_storage():
    """各テストの前後でインメモリストレージを確実にクリア"""
    from app.services import _custid_by_email, _customers_by_id, _lock

    with _lock:
        _customers_by_id.clear()
        _custid_by_email.clear()
    try:
        yield
    finally:
        with _lock:
            _customers_by_id.clear()
            _custid_by_email.clear()
