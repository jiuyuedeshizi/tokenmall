import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.bailian_native import router as bailian_native_router
from app.api.deps import get_api_key_entity
from app.db.session import get_db


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):  # noqa: ARG002
        return self

    def first(self):
        return self.result


class FakeDB:
    def __init__(self, user):
        self.user = user

    def query(self, _entity):
        return FakeQuery(self.user)


class BailianNativeRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(bailian_native_router)
        self.user = SimpleNamespace(id=7, status="active")
        self.api_key = SimpleNamespace(user_id=7)
        self.app.dependency_overrides[get_api_key_entity] = lambda: self.api_key
        self.app.dependency_overrides[get_db] = lambda: FakeDB(self.user)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.client.close()

    def test_image_generation_route_forwards_and_uses_usage_fallback(self):
        async def fake_forward_request(request, provider_url, api_key, provider_headers=None):  # noqa: ARG001
            self.assertEqual(
                await request.body(),
                b'{"model":"qwen-image-2.0-pro","input":{"messages":[{"role":"user","content":[{"text":"draw"}]}]}}',
            )
            return JSONResponse(
                status_code=200,
                content={
                    "request_id": "img_req_1",
                    "output": {
                        "results": [
                            {"url": "https://example.com/1.png"},
                            {"url": "https://example.com/2.png"},
                        ]
                    },
                },
            )

        with (
            patch("app.api.bailian_native.resolve_bailian_multimodal_generation_route", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen-image-2.0-pro"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request", return_value="req_image"),
            patch("app.api.bailian_native.forward_request", side_effect=fake_forward_request),
            patch("app.api.bailian_native.after_response") as after_response,
            patch("app.api.bailian_native.on_error") as on_error,
        ):
            response = self.client.post(
                "/api/v1/services/aigc/multimodal-generation/generation",
                content=b'{"model":"qwen-image-2.0-pro","input":{"messages":[{"role":"user","content":[{"text":"draw"}]}]}}',
                headers={"Authorization": "Bearer tk_live_unit", "Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        after_response.assert_called_once()
        usage = after_response.call_args.kwargs["response_payload"]["usage"]
        self.assertEqual(usage["image_count"], 2)
        on_error.assert_not_called()

    def test_tts_route_forwards_and_estimates_char_usage(self):
        raw_body = (
            b'{"model":"qwen3-tts-vd-2026-01-26","input":{"text":"\xe4\xbd\xa0\xe5\xa5\xbd","voice":"Cherry","language_type":"Chinese"}}'
        )

        async def fake_forward_request(request, provider_url, api_key, provider_headers=None):  # noqa: ARG001
            self.assertEqual(await request.body(), raw_body)
            return JSONResponse(
                status_code=200,
                content={
                    "request_id": "tts_req_1",
                    "output": {
                        "audio": {
                            "url": "https://example.com/audio.wav",
                        }
                    },
                },
            )

        with (
            patch("app.api.bailian_native.resolve_bailian_multimodal_generation_route", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen3-tts-vd-2026-01-26", billing_mode="per_10k_chars"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request", return_value="req_tts"),
            patch("app.api.bailian_native.forward_request", side_effect=fake_forward_request),
            patch("app.api.bailian_native.after_response") as after_response,
            patch("app.api.bailian_native.on_error") as on_error,
        ):
            response = self.client.post(
                "/api/v1/services/aigc/multimodal-generation/generation",
                content=raw_body,
                headers={"Authorization": "Bearer tk_live_unit", "Content-Type": "application/json"},
            )

        self.assertEqual(response.status_code, 200)
        usage = after_response.call_args.kwargs["response_payload"]["usage"]
        self.assertEqual(usage["char_count"], 2)
        on_error.assert_not_called()

    def test_tts_stream_route_uses_estimated_character_fallback(self):
        raw_body = b'{"model":"qwen3-tts-vd-2026-01-26","input":{"text":"hello","voice":"Cherry","language_type":"Chinese"}}'

        async def fake_forward_stream(request, provider_url, api_key, provider_headers=None):  # noqa: ARG001
            self.assertEqual(await request.body(), raw_body)
            return (
                JSONResponse(status_code=200, content={"streamed": True}),
                {"usage": None, "upstream_id": "tts_stream_1", "output_text": ""},
            )

        with (
            patch("app.api.bailian_native.resolve_bailian_multimodal_generation_route", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen3-tts-vd-2026-01-26", billing_mode="per_10k_chars"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request", return_value="req_tts_stream"),
            patch("app.api.bailian_native.forward_stream", side_effect=fake_forward_stream),
            patch("app.api.bailian_native.after_estimated_character_response") as after_estimated_character_response,
            patch("app.api.bailian_native.after_response") as after_response,
            patch("app.api.bailian_native.on_error") as on_error,
        ):
            response = self.client.post(
                "/api/v1/services/aigc/multimodal-generation/generation",
                content=raw_body,
                headers={
                    "Authorization": "Bearer tk_live_unit",
                    "Content-Type": "application/json",
                    "X-DashScope-SSE": "enable",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["streamed"], True)
        after_estimated_character_response.assert_called_once()
        after_response.assert_not_called()
        on_error.assert_not_called()
