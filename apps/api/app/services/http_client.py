import httpx

from app.core.config import settings

_proxy_http_client: httpx.AsyncClient | None = None


def get_proxy_http_client() -> httpx.AsyncClient:
    global _proxy_http_client
    if _proxy_http_client is None:
        _proxy_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.proxy_http_connect_timeout_seconds,
                read=settings.proxy_http_read_timeout_seconds,
                write=settings.proxy_http_write_timeout_seconds,
                pool=settings.proxy_http_pool_timeout_seconds,
            ),
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50, keepalive_expiry=30.0),
        )
    return _proxy_http_client


async def close_proxy_http_client() -> None:
    global _proxy_http_client
    if _proxy_http_client is None:
        return
    await _proxy_http_client.aclose()
    _proxy_http_client = None
