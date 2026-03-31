import httpx

_proxy_http_client: httpx.AsyncClient | None = None


def get_proxy_http_client() -> httpx.AsyncClient:
    global _proxy_http_client
    if _proxy_http_client is None:
        _proxy_http_client = httpx.AsyncClient(
            timeout=None,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50, keepalive_expiry=30.0),
        )
    return _proxy_http_client


async def close_proxy_http_client() -> None:
    global _proxy_http_client
    if _proxy_http_client is None:
        return
    await _proxy_http_client.aclose()
    _proxy_http_client = None
