from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


@lru_cache(maxsize=1)
def get_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    connect_args = {"check_same_thread"} if url.startswith("sqlite") else {}
    return create_engine(url, echo=False, future=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_sessionmaker():
    return sessionmaker(
        bind=get_engine(), autoflush=False, autocommit=False, future=True
    )
