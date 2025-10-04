# tests/conftest.py
import copy
import logging.config

import pytest
from fastapi.testclient import TestClient

from app.main import LOGGING_CONFIG


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


@pytest.fixture
def audit_log_file(tmp_path, monkeypatch, request):
    """ログファイルを一時ディレクトリに設定、テスト後に元に戻す"""
    log_file = tmp_path / "auth_audit.log"

    # 元の設定を保存 (deep copy)
    original_config = copy.deepcopy(LOGGING_CONFIG)

    # 一時的なログファイルパスに変更
    monkeypatch.setitem(LOGGING_CONFIG["handlers"]["file"], "filename", str(log_file))

    # ロギング設定を適用
    logging.config.dictConfig(LOGGING_CONFIG)

    # テスト終了後に元の設定を復元
    def restore_logging():
        logging.config.dictConfig(original_config)

    request.addfinalizer(restore_logging)

    return log_file
