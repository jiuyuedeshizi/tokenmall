import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.api.bailian_native import router as bailian_native_router
from app.api.deps import get_api_key_entity_async
from app.db.session import get_async_db


class FakeDB:
    def __init__(self, user):
        self.user = user

    async def execute(self, _statement):
        return SimpleNamespace(scalar_one_or_none=lambda: self.user)


class BailianNativeRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(bailian_native_router)
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
            patch("app.api.bailian_native.resolve_bailian_multimodal_generation_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen-image-2.0-pro"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request_async", return_value="req_image"),
            patch("app.api.bailian_native.forward_request", side_effect=fake_forward_request),
            patch("app.api.bailian_native.after_response_async") as after_response,
            patch("app.api.bailian_native.on_error_async") as on_error,
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
            patch("app.api.bailian_native.resolve_bailian_multimodal_generation_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen3-tts-vd-2026-01-26", billing_mode="per_10k_chars"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request_async", return_value="req_tts"),
            patch("app.api.bailian_native.forward_request", side_effect=fake_forward_request),
            patch("app.api.bailian_native.after_response_async") as after_response,
            patch("app.api.bailian_native.on_error_async") as on_error,
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
            patch("app.api.bailian_native.resolve_bailian_multimodal_generation_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="qwen3-tts-vd-2026-01-26", billing_mode="per_10k_chars"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request_async", return_value="req_tts_stream"),
            patch("app.api.bailian_native.forward_stream", side_effect=fake_forward_stream),
            patch("app.api.bailian_native.after_estimated_character_response_async") as after_estimated_character_response,
            patch("app.api.bailian_native.after_response_async") as after_response,
            patch("app.api.bailian_native.on_error_async") as on_error,
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

    def test_video_synthesis_route_forwards_and_bills_by_duration(self):
        raw_body = (
            b'{"model":"wan2.6-i2v-flash","input":{"prompt":"run","img_url":"https://example.com/cat.png"},"parameters":{"audio":false,"resolution":"720P","duration":5}}'
        )

        async def fake_forward_request(request, provider_url, api_key, provider_headers=None, method="POST"):  # noqa: ARG001
            self.assertEqual(method, "POST")
            self.assertEqual(await request.body(), raw_body)
            return JSONResponse(
                status_code=200,
                content={
                    "request_id": "video_req_1",
                    "output": {
                        "task_id": "task_video_1",
                        "task_status": "PENDING",
                    },
                },
            )

        with (
            patch("app.api.bailian_native.resolve_bailian_video_synthesis_route_async", return_value=SimpleNamespace(model=SimpleNamespace(model_code="wan2.6-i2v-flash", billing_mode="per_second"), provider_url="https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis", provider_api_key="provider-secret", provider_headers={})),
            patch("app.api.bailian_native.before_request_async", return_value="req_video"),
            patch("app.api.bailian_native.forward_request", side_effect=fake_forward_request),
            patch("app.api.bailian_native.after_response_async") as after_response,
            patch("app.api.bailian_native.on_error_async") as on_error,
        ):
            response = self.client.post(
                "/api/v1/services/aigc/video-generation/video-synthesis",
                content=raw_body,
                headers={
                    "Authorization": "Bearer tk_live_unit",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
            )

        self.assertEqual(response.status_code, 200)
        usage = after_response.call_args.kwargs["response_payload"]["usage"]
        self.assertEqual(usage["second_count"], 5)
        self.assertEqual(usage["resolution"], "720P")
        self.assertEqual(usage["audio"], False)
        on_error.assert_not_called()

    def test_task_status_route_forwards_get(self):
        async def fake_forward_request(request, provider_url, api_key, provider_headers=None, method="POST"):  # noqa: ARG001
            self.assertEqual(method, "GET")
            self.assertTrue(provider_url.endswith("/api/v1/tasks/task_123"))
            return JSONResponse(
                status_code=200,
                content={"output": {"task_id": "task_123", "task_status": "SUCCEEDED"}},
            )

        with patch("app.api.bailian_native.forward_request", side_effect=fake_forward_request):
            response = self.client.get(
                "/api/v1/tasks/task_123",
                headers={"Authorization": "Bearer tk_live_unit"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["output"]["task_status"], "SUCCEEDED")
