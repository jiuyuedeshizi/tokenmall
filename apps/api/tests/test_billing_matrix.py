from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.models import UsageLog
from app.services.official_model_catalog import OFFICIAL_MODEL_CATALOG
from app.services.proxy import after_response


class CaptureDB:
    def __init__(self):
        self.added = []

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        pass


def build_api_key():
    return SimpleNamespace(
        id=1,
        used_tokens=0,
        used_requests=0,
        used_amount=Decimal("0.0000"),
        last_used_at=None,
        budget_limit=None,
        token_limit=None,
        request_limit=None,
        status="active",
    )


def build_model(model_code: str):
    item = OFFICIAL_MODEL_CATALOG[model_code]
    return SimpleNamespace(
        model_code=model_code,
        billing_mode=item["billing_mode"],
        pricing_items=item["pricing_items"],
        input_price_per_million=item["input_price_per_million"],
        output_price_per_million=item["output_price_per_million"],
        display_name=item["display_name"],
    )


def build_usage(model_code: str, billing_mode: str) -> tuple[dict, int, Decimal]:
    if billing_mode == "token":
        usage = {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200}
        if model_code == "qwen-plus":
            return usage, 200, Decimal("0.000480")
        if model_code == "qwen-flash":
            return usage, 200, Decimal("0.000184")
        if model_code == "deepseek-v3.2":
            return usage, 200, Decimal("0.000480")
        if model_code == "kimi-k2.5":
            return usage, 200, Decimal("0.002160")
        if model_code == "glm-5":
            return usage, 200, Decimal("0.001920")
        if model_code == "minimax-m2.5":
            return usage, 200, Decimal("0.000924")
    if billing_mode == "per_image":
        if model_code == "qwen-image-2.0":
            return {"image_count": 1}, 1, Decimal("0.200000")
        if model_code == "qwen-image-2.0-pro":
            return {"image_count": 1}, 1, Decimal("0.500000")
    if billing_mode == "per_second":
        if model_code == "wan2.6-i2v-flash":
            return {"second_count": 5, "resolution": "720P", "audio": False}, 5, Decimal("0.750000")
        if model_code == "qwen3-asr-flash":
            return {"seconds": 1}, 1, Decimal("0.000220")
    if billing_mode == "per_10k_chars":
        return {"char_count": 2000}, 2000, Decimal("0.160000")
    raise AssertionError(f"Unhandled model: {model_code}")


def test_official_model_billing_matrix():
    user = SimpleNamespace(id=7)

    for model_code, item in OFFICIAL_MODEL_CATALOG.items():
        api_key = build_api_key()
        model = build_model(model_code)
        usage, expected_tokens, expected_amount = build_usage(model_code, item["billing_mode"])
        db = CaptureDB()

        with patch("app.services.proxy.capture_usage_reservation"):
            after_response(
                api_key=api_key,
                user=user,
                model=model,
                request_id=f"req_{model_code}",
                response_payload={"id": f"resp_{model_code}", "usage": usage},
                response_time_ms=123,
                db=db,
            )

        usage_log = next(entity for entity in db.added if isinstance(entity, UsageLog))
        assert usage_log.model_code == model_code
        assert usage_log.total_tokens == expected_tokens
        assert usage_log.amount == expected_amount
        assert api_key.used_tokens == expected_tokens
        assert api_key.used_requests == 1
        assert api_key.used_amount == expected_amount
