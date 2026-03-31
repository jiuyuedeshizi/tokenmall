import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.api import admin as admin_api
from app.api import models as models_api


def build_row(model_code: str, **overrides):
    base = {
        "id": 1,
        "provider": "alibaba-bailian",
        "model_id": model_code,
        "model_code": model_code,
        "capability_type": "chat",
        "display_name": model_code,
        "vendor_display_name": "Alibaba",
        "category": "text",
        "billing_mode": "token",
        "pricing_items": "[]",
        "input_price_per_million": Decimal("1"),
        "output_price_per_million": Decimal("2"),
        "description": "desc",
        "hero_description": "hero",
        "rating": Decimal("4.8"),
        "support_features": "文本生成",
        "tags": "文本生成",
        "example_python": "",
        "example_typescript": "",
        "example_curl": "",
        "is_active": True,
        "created_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class ModelExamplesFallbackTests(unittest.TestCase):
    def test_public_model_serializer_uses_official_example_fallback(self):
        payload = models_api.serialize_model(build_row("glm-5"))

        self.assertIn("glm-5", payload["example_python"])
        self.assertIn("TypeScript", payload["example_python"])
        self.assertTrue(payload["example_typescript"])
        self.assertTrue(payload["example_curl"])

    def test_admin_model_serializer_prefers_database_example_over_fallback(self):
        payload = admin_api.serialize_model(
            build_row("deepseek-v3.2", example_python="print('custom-example')")
        )

        self.assertEqual(payload["example_python"], "print('custom-example')")
        self.assertTrue(payload["example_typescript"])
        self.assertTrue(payload["example_curl"])


if __name__ == "__main__":
    unittest.main()
