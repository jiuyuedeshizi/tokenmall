from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.services.observability import reset_metrics


@pytest.fixture(autouse=True)
def reset_observability_state():
    reset_metrics()
    yield
    reset_metrics()


@pytest.fixture
def sqlite_db_urls(tmp_path: Path) -> dict[str, str]:
    db_path = tmp_path / "tokenmall-test.sqlite"
    return {
        "sync": f"sqlite:///{db_path}",
        "async": f"sqlite+aiosqlite:///{db_path}",
        "path": str(db_path),
    }


@pytest.fixture
def sync_session_factory(sqlite_db_urls: dict[str, str]):
    engine = create_engine(sqlite_db_urls["sync"], connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def async_session_factory(sync_session_factory, sqlite_db_urls: dict[str, str]):  # noqa: ARG001
    engine = create_async_engine(sqlite_db_urls["async"], future=True)
    factory = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        import asyncio

        asyncio.run(engine.dispose())
