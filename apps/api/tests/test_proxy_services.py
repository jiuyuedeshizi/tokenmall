import asyncio
import json
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from app.services.proxy import after_estimated_stream_response, before_request, forward_request, forward_stream
from app.services.routing import resolve_chat_route


def build_request(body: bytes, headers: dict[str, str] | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/chat/completions",
        "headers": [
            (key.lower().encode("utf-8"), value.encode("utf-8"))
            for key, value in (headers or {"content-type": "application/json"}).items()
        ],
    }

    received = False

    async def receive():
        nonlocal received
        if received:
            return {"type": "http.request", "body": b"", "more_body": False}
        received = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(scope, receive)


class FakeQuery:
    def __init__(self, model):
        self.model = model

    def filter(self, *args, **kwargs):  # noqa: ARG002
        return self

    def first(self):
        return self.model


class FakeDB:
    def __init__(self, model):
        self.model = model

    def query(self, _entity):
        return FakeQuery(self.model)


class FakeAsyncClientNonStream:
    response: httpx.Response | None = None
    captured_content: bytes | None = None
    captured_headers: dict[str, str] | None = None
    captured_url: str | None = None

    def __init__(self, timeout=None):  # noqa: ARG002
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):  # noqa: ARG002
        return False

    async def post(self, url, content=None, headers=None):
        type(self).captured_url = url
        type(self).captured_content = content
        type(self).captured_headers = headers
        return type(self).response


class FakeStreamingResponse:
    def __init__(self, status_code=200, headers=None, chunks=None):
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {"content-type": "text/event-stream"})
        self._chunks = chunks or []
        self.closed = False

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk

    async def aread(self):
        return b"".join(self._chunks)

    async def aclose(self):
        self.closed = True


class FakeAsyncClientStream:
    response = None
    captured_request = None
    closed = False

    def __init__(self, timeout=None):  # noqa: ARG002
        pass

    def build_request(self, method, url, content=None, headers=None):
        request = httpx.Request(method, url, content=content, headers=headers)
        type(self).captured_request = request
        return request

    async def send(self, request, stream=False):  # noqa: ARG002
        type(self).captured_request = request
        return type(self).response

    async def aclose(self):
        type(self).closed = True


class ProxyServicesTests(unittest.IsolatedAsyncioTestCase):
    async def test_forward_request_keeps_body_and_rewrites_authorization(self):
        body = json.dumps({"model": "qwen-plus", "messages": [{"role": "user", "content": "hi"}]}).encode("utf-8")
        request = build_request(body, headers={"content-type": "application/json", "authorization": "Bearer client-key"})
        FakeAsyncClientNonStream.response = httpx.Response(
            200,
            headers={"content-type": "application/json", "x-upstream": "ok"},
            content=b'{"id":"resp_1","usage":{"prompt_tokens":1,"completion_tokens":2,"total_tokens":3}}',
            request=httpx.Request("POST", "https://unit.test/chat/completions"),
        )

        with patch("app.services.proxy.httpx.AsyncClient", FakeAsyncClientNonStream):
            response = await forward_request(
                request=request,
                provider_url="https://unit.test/chat/completions",
                api_key="provider-secret",
                provider_headers={"x-provider": "bailian"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FakeAsyncClientNonStream.captured_content, body)
        self.assertEqual(FakeAsyncClientNonStream.captured_url, "https://unit.test/chat/completions")
        self.assertEqual(FakeAsyncClientNonStream.captured_headers["authorization"], "Bearer provider-secret")
        self.assertEqual(FakeAsyncClientNonStream.captured_headers["x-provider"], "bailian")
        self.assertNotIn("host", {key.lower() for key in FakeAsyncClientNonStream.captured_headers})

    async def test_forward_stream_yields_chunks_and_collects_usage(self):
        chunks = [
            b'data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"he"}}]}\n\n',
            b'data: {"id":"chatcmpl-1","usage":{"prompt_tokens":11,"completion_tokens":7,"total_tokens":18}}\n\n',
            b"data: [DONE]\n\n",
        ]
        FakeAsyncClientStream.response = FakeStreamingResponse(chunks=chunks)
        FakeAsyncClientStream.closed = False
        request = build_request(b'{"model":"qwen-plus","stream":true}', headers={"authorization": "Bearer client"})

        with patch("app.services.proxy.httpx.AsyncClient", FakeAsyncClientStream):
            response, state = await forward_stream(
                request=request,
                provider_url="https://unit.test/chat/completions",
                api_key="provider-secret",
                provider_headers=None,
            )
            streamed = []
            async for chunk in response.body_iterator:
                streamed.append(chunk)

        self.assertEqual(streamed, chunks)
        self.assertEqual(state["upstream_id"], "chatcmpl-1")
        self.assertEqual(state["usage"]["total_tokens"], 18)
        self.assertEqual(FakeAsyncClientStream.captured_request.headers["authorization"], "Bearer provider-secret")
        self.assertTrue(FakeAsyncClientStream.response.closed)
        self.assertTrue(FakeAsyncClientStream.closed)

    async def test_forward_stream_surfaces_upstream_error_payload(self):
        FakeAsyncClientStream.response = FakeStreamingResponse(
            status_code=429,
            headers={"content-type": "application/json"},
            chunks=[b'{"error":{"message":"rate limit","type":"rate_limit_exceeded"}}'],
        )
        request = build_request(b'{"model":"qwen-plus","stream":true}')

        with patch("app.services.proxy.httpx.AsyncClient", FakeAsyncClientStream):
            response, state = await forward_stream(
                request=request,
                provider_url="https://unit.test/chat/completions",
                api_key="provider-secret",
            )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(state, {})
        payload = json.loads(response.body.decode("utf-8"))
        self.assertEqual(payload["error"]["message"], "rate limit")

    async def test_before_request_rejects_budget_exceeded(self):
        api_key = SimpleNamespace(
            id=1,
            status="active",
            token_limit=None,
            request_limit=None,
            budget_limit=Decimal("0.0001"),
            used_tokens=0,
            used_requests=0,
            used_amount=Decimal("0.0000"),
        )
        user = SimpleNamespace(id=1, status="active")
        model = SimpleNamespace(
            model_code="qwen-plus",
            billing_mode="token",
            input_price_per_million=Decimal("1"),
            output_price_per_million=Decimal("1"),
            display_name="Qwen Plus",
        )
        payload = {"messages": [{"role": "user", "content": "hello"}], "max_tokens": 500}

        with (
            patch("app.services.proxy.get_wallet_account", return_value=SimpleNamespace(balance=Decimal("10"), reserved_balance=Decimal("0"))),
            patch("app.services.proxy.create_usage_reservation") as create_reservation,
            patch("app.services.proxy.estimate_prompt_tokens", return_value=500),
        ):
            with self.assertRaises(HTTPException) as ctx:
                before_request(api_key=api_key, user=user, payload=payload, model=model, db=object())

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("预算", str(ctx.exception.detail))
        create_reservation.assert_not_called()

    async def test_after_estimated_stream_response_uses_local_token_estimate(self):
        api_key = SimpleNamespace(
            id=1,
            status="active",
            budget_limit=None,
            token_limit=None,
            request_limit=None,
            used_tokens=0,
            used_requests=0,
            used_amount=Decimal("0.0000"),
            last_used_at=None,
        )
        user = SimpleNamespace(id=1)
        model = SimpleNamespace(
            model_code="qwen-plus",
            billing_mode="token",
            input_price_per_million=Decimal("1.0"),
            output_price_per_million=Decimal("2.0"),
            display_name="Qwen Plus",
        )
        db = SimpleNamespace(add=lambda value: None, commit=lambda: None)

        with (
            patch("app.services.proxy.capture_usage_reservation") as capture_usage_reservation,
            patch("app.services.proxy.estimate_prompt_tokens", return_value=10),
            patch("app.services.proxy.count_text_tokens", return_value=6),
        ):
            after_estimated_stream_response(
                api_key=api_key,
                user=user,
                model=model,
                request_id="req_1",
                payload={"messages": [{"role": "user", "content": "hello"}]},
                output_text="One, two, three!",
                upstream_id="chatcmpl-estimated",
                response_time_ms=120,
                db=db,
            )

        self.assertEqual(api_key.used_tokens, 16)
        self.assertEqual(api_key.used_requests, 1)
        capture_usage_reservation.assert_called_once()
        self.assertEqual(capture_usage_reservation.call_args.kwargs["billing_source"], "estimated_stream")


class RoutingTests(unittest.TestCase):
    def test_resolve_chat_route_for_bailian(self):
        model = SimpleNamespace(
            provider="alibaba-bailian",
            model_code="qwen-plus",
            model_id="qwen-plus",
            is_active=True,
        )
        with patch("app.services.routing.get_bailian_provider_config", return_value=SimpleNamespace(base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key="bk", headers={})):
            route = resolve_chat_route("qwen-plus", FakeDB(model))

        self.assertEqual(route.provider_url, "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
        self.assertEqual(route.provider_api_key, "bk")

    def test_resolve_chat_route_rejects_tencent_placeholder(self):
        model = SimpleNamespace(
            provider="tencent",
            model_code="hunyuan-turbos-latest",
            model_id="hunyuan-turbos-latest",
            is_active=True,
        )
        with patch("app.services.routing.get_tencent_provider_config", return_value=SimpleNamespace(base_url="", api_key="", headers={})):
            with self.assertRaises(HTTPException) as ctx:
                resolve_chat_route("hunyuan-turbos-latest", FakeDB(model))

        self.assertEqual(ctx.exception.status_code, 501)
        self.assertIn("预留配置", str(ctx.exception.detail))
