from functools import lru_cache

from .adapters.memory_uow import MemoryUoW


@lru_cache(maxsize=1)
def _memory_uow_singleton() -> MemoryUoW:
    return MemoryUoW()


def get_uow():
    return _memory_uow_singleton()


def reset_uow_for_tests() -> MemoryUoW:
    _memory_uow_singleton.cache_clear()
    return _memory_uow_singleton()
