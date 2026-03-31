import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import proxy as proxy_api
from app.api.deps import get_api_key_entity_async
from app.db.session import get_async_db
from app.main import http_exception_wrapper, unhandled_exception_wrapper


class FakeDB:
    def __init__(self, user):
        self.user = user

    async def execute(self, _statement):
        return SimpleNamespace(scalar_one_or_none=lambda: self.user)


class ProxyRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.add_exception_handler(Exception, unhandled_exception_wrapper)
        self.app.add_exception_handler(HTTPException, http_exception_wrapper)
        self.app.include_router(proxy_api.router, prefix="/v1")
        self.user = SimpleNamespace(id=7, status="active")
        self.api_key = SimpleNamespace(user_id=7)
        async def fake_api_key_dependency():
            return self.api_key

        async def fake_db_dependency():
            return FakeDB(self.user)

        self.app.dependency_overrides[get_api_key_entity_async] = fake_api_key_dependency
        self.app.dependency_overrides[get_async_db] = fake_db_dependency
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_invalid_json_returns_openai_style_error(self):
        response = self.client.post(
            "/v1/chat/completions",
            content=b"{not-json",
            headers={"Authorization": "Bearer tk_live_unit", "Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["type"], "invalid_request_error")

    def test_non_stream_route_forwards_raw_body(self):
        raw_body = b'{"model":"qwen-plus","messages":[{"role":"user","content":"hello"}]}'

        async def fake_forward_request(request, provider_url, api_key, provider_headers=None, body_override=None):
            self.assertEqual(await request.body(), raw_body)
            self.assertIsNone(body_override)
            self.assertEqual(provider_url, "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
            self.assertEqual(api_key, "provider-secret")
            return proxy_api.JSONResponse(
                status_code=200,
                content={
                    "id": "chatcmpl-1",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                },
            )

        with (
            patch.object(proxy_api, "resolve_chat_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen-plus"), provider_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", provider_api_key="provider-secret", provider_headers={})),
            patch.object(proxy_api, "before_request_async", return_value="req_123"),
            patch.object(proxy_api, "forward_request", side_effect=fake_forward_request),
            patch.object(proxy_api, "after_response_async") as after_response,
            patch.object(proxy_api, "on_error_async") as on_error,
        ):
            response = self.client.post(
                "/v1/chat/completions",
                content=raw_body,
                headers={"Authorization": "Bearer tk_live_unit", "Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "chatcmpl-1")
        after_response.assert_called_once()
        on_error.assert_not_called()

    def test_non_stream_route_rewrites_model_for_upstream_alias(self):
        raw_body = b'{"model":"minimax-m2.5","messages":[{"role":"user","content":"hello"}]}'
        expected_upstream_body = b'{"model": "MiniMax-M2.5", "messages": [{"role": "user", "content": "hello"}]}'

        async def fake_forward_request(request, provider_url, api_key, provider_headers=None, method="POST", body_override=None):  # noqa: ARG001
            self.assertEqual(await request.body(), raw_body)
            self.assertEqual(body_override, expected_upstream_body)
            self.assertEqual(provider_url, "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
            self.assertEqual(api_key, "provider-secret")
            return proxy_api.JSONResponse(
                status_code=200,
                content={
                    "id": "chatcmpl-minimax",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                },
            )

        with (
            patch.object(proxy_api, "resolve_chat_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="minimax-m2.5"), upstream_model_id="MiniMax-M2.5", provider_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", provider_api_key="provider-secret", provider_headers={})),
            patch.object(proxy_api, "before_request_async", return_value="req_minimax"),
            patch.object(proxy_api, "forward_request", side_effect=fake_forward_request),
            patch.object(proxy_api, "after_response_async") as after_response,
            patch.object(proxy_api, "on_error_async") as on_error,
        ):
            response = self.client.post(
                "/v1/chat/completions",
                content=raw_body,
                headers={"Authorization": "Bearer tk_live_unit", "Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "chatcmpl-minimax")
        after_response.assert_called_once()
        on_error.assert_not_called()

    def test_stream_route_uses_bailian_estimated_fallback_when_usage_missing(self):
        raw_body = b'{"model":"qwen-plus","messages":[{"role":"user","content":"hello"}],"stream":true}'

        async def fake_forward_stream(request, provider_url, api_key, provider_headers=None, body_override=None):  # noqa: ARG001
            self.assertEqual(await request.body(), raw_body)
            self.assertIsNone(body_override)
            return (
                proxy_api.JSONResponse(status_code=200, content={"streamed": True}),
                {"usage": None, "upstream_id": "chatcmpl-stream", "output_text": "One, two, three!"},
            )

        with (
            patch.object(proxy_api, "resolve_chat_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen-plus"), provider_name="alibaba-bailian", provider_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", provider_api_key="provider-secret", provider_headers={})),
            patch.object(proxy_api, "before_request_async", return_value="req_stream"),
            patch.object(proxy_api, "forward_stream", side_effect=fake_forward_stream),
            patch.object(proxy_api, "after_estimated_stream_response_async") as after_estimated_stream_response,
            patch.object(proxy_api, "after_response_async") as after_response,
            patch.object(proxy_api, "on_error_async") as on_error,
        ):
            response = self.client.post(
                "/v1/chat/completions",
                content=raw_body,
                headers={"Authorization": "Bearer tk_live_unit", "Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["streamed"], True)
        after_estimated_stream_response.assert_called_once()
        after_response.assert_not_called()
        on_error.assert_not_called()
