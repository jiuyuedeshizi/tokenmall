from app.db.session import _build_async_engine_kwargs, _build_sync_engine_kwargs
from app.services.http_client import close_proxy_http_client, get_proxy_http_client


def test_proxy_http_client_uses_bounded_timeouts():
    client = get_proxy_http_client()
    try:
        assert client.timeout.connect is not None
        assert client.timeout.read is not None
        assert client.timeout.write is not None
        assert client.timeout.pool is not None
    finally:
        import asyncio

        asyncio.run(close_proxy_http_client())


def test_postgres_engine_kwargs_enable_pool_tuning():
    sync_kwargs = _build_sync_engine_kwargs("postgresql+psycopg://postgres:postgres@localhost:5432/tokenmall")
    async_kwargs = _build_async_engine_kwargs("postgresql+psycopg://postgres:postgres@localhost:5432/tokenmall")

    assert sync_kwargs["pool_size"] == 20
    assert sync_kwargs["max_overflow"] == 40
    assert sync_kwargs["pool_timeout"] == 30
    assert sync_kwargs["pool_recycle"] == 1800
    assert sync_kwargs["pool_pre_ping"] is True
    assert async_kwargs["pool_size"] == 20
    assert async_kwargs["max_overflow"] == 40
    assert async_kwargs["pool_timeout"] == 30
    assert async_kwargs["pool_recycle"] == 1800
    assert async_kwargs["pool_pre_ping"] is True


def test_sqlite_engine_kwargs_skip_pool_overrides():
    sync_kwargs = _build_sync_engine_kwargs("sqlite:///tmp.db")
    async_kwargs = _build_async_engine_kwargs("sqlite:///tmp.db")

    assert sync_kwargs == {"future": True}
    assert async_kwargs == {"future": True}
