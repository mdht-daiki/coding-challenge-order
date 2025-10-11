from __future__ import annotations

import os
from functools import lru_cache
from typing import Callable

from .adapters.memory_uow import MemoryUoW
from .adapters.sqlalchemy_uow import SqlAlchemyUoW
from .ports import UoW

_uow_factory: Callable[[], UoW] | None = None


@lru_cache(maxsize=1)
def _memory_singleton() -> MemoryUoW:
    return MemoryUoW()


def _memory_factory() -> UoW:
    return _memory_singleton()


def _sqlalchemy_factory() -> UoW:
    return SqlAlchemyUoW()


def set_uow_factory(factory: Callable[[], UoW]) -> None:
    global _uow_factory
    _uow_factory = factory


def reset_memory_singleton() -> None:
    _memory_singleton.cache_clear()


def get_uow():
    global _uow_factory
    if _uow_factory is None:
        use_db = os.getenv("USE_DB", "0") == "1"
        set_uow_factory(_sqlalchemy_factory if use_db else _memory_factory)
    return _uow_factory()


# テスト用ユーティリティ


def force_memory_mode():
    set_uow_factory(_memory_factory)
    reset_memory_singleton()


def force_db_mode():
    set_uow_factory(_sqlalchemy_factory)
