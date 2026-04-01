from datetime import datetime
from decimal import Decimal

from app.api.usage import list_usage_logs
from app.models import ModelCatalog, UsageLog, User


def test_usage_logs_formats_quantity_by_billing_mode(sync_session_factory):
    session = sync_session_factory()
    user = User(
        email="usage@example.com",
        phone=None,
        password_hash="hashed",
        name="Usage Tester",
        role="user",
        status="active",
    )
    session.add(user)
    session.flush()

    session.add_all([
        ModelCatalog(
            provider="alibaba-bailian",
            model_code="wan2.6-i2v-flash",
            model_id="wan2.6-i2v-flash",
            capability_type="video_generation",
            display_name="Wan 2.6 I2V Flash",
            vendor_display_name="DashScope",
            category="video",
            billing_mode="per_second",
            pricing_items="[]",
            input_price_per_million=Decimal("0.0000"),
            output_price_per_million=Decimal("0.0000"),
            description="",
            hero_description="",
            support_features="",
            tags="",
            example_python="",
            example_typescript="",
            example_curl="",
        ),
        ModelCatalog(
            provider="alibaba-bailian",
            model_code="qwen-image-2.0-pro",
            model_id="qwen-image-2.0-pro",
            capability_type="image_generation",
            display_name="Qwen Image 2.0 Pro",
            vendor_display_name="DashScope",
            category="image",
            billing_mode="per_image",
            pricing_items="[]",
            input_price_per_million=Decimal("0.0000"),
            output_price_per_million=Decimal("0.0000"),
            description="",
            hero_description="",
            support_features="",
            tags="",
            example_python="",
            example_typescript="",
            example_curl="",
        ),
        ModelCatalog(
            provider="alibaba-bailian",
            model_code="qwen3-tts-vd-2026-01-26",
            model_id="qwen3-tts-vd-2026-01-26",
            capability_type="audio_generation",
            display_name="Qwen TTS",
            vendor_display_name="DashScope",
            category="audio",
            billing_mode="per_10k_chars",
            pricing_items="[]",
            input_price_per_million=Decimal("0.0000"),
            output_price_per_million=Decimal("0.0000"),
            description="",
            hero_description="",
            support_features="",
            tags="",
            example_python="",
            example_typescript="",
            example_curl="",
        ),
        ModelCatalog(
            provider="alibaba-bailian",
            model_code="minimax-m2.5",
            model_id="minimax-m2.5",
            capability_type="chat",
            display_name="MiniMax M2.5",
            vendor_display_name="DashScope",
            category="chat",
            billing_mode="token",
            pricing_items="[]",
            input_price_per_million=Decimal("0.0000"),
            output_price_per_million=Decimal("0.0000"),
            description="",
            hero_description="",
            support_features="",
            tags="",
            example_python="",
            example_typescript="",
            example_curl="",
        ),
    ])
    session.add_all([
        UsageLog(
            user_id=user.id,
            api_key_id=None,
            request_id="req-video",
            model_code="wan2.6-i2v-flash",
            input_tokens=0,
            output_tokens=0,
            total_tokens=5,
            amount=Decimal("0.7500"),
            billing_source="provider_usage",
            status="success",
            error_message="",
            created_at=datetime(2026, 3, 31, 10, 0),
        ),
        UsageLog(
            user_id=user.id,
            api_key_id=None,
            request_id="req-image",
            model_code="qwen-image-2.0-pro",
            input_tokens=0,
            output_tokens=0,
            total_tokens=1,
            amount=Decimal("0.5000"),
            billing_source="provider_usage",
            status="success",
            error_message="",
            created_at=datetime(2026, 3, 31, 9, 0),
        ),
        UsageLog(
            user_id=user.id,
            api_key_id=None,
            request_id="req-tts",
            model_code="qwen3-tts-vd-2026-01-26",
            input_tokens=2000,
            output_tokens=0,
            total_tokens=2000,
            amount=Decimal("0.1200"),
            billing_source="provider_usage",
            status="success",
            error_message="",
            created_at=datetime(2026, 3, 31, 8, 0),
        ),
        UsageLog(
            user_id=user.id,
            api_key_id=None,
            request_id="req-chat",
            model_code="minimax-m2.5",
            input_tokens=120,
            output_tokens=79,
            total_tokens=199,
            amount=Decimal("0.0014"),
            billing_source="provider_usage",
            status="success",
            error_message="",
            created_at=datetime(2026, 3, 31, 7, 0),
        ),
    ])
    session.commit()

    result = list_usage_logs(
        keyword="",
        event_type="all",
        range_days=None,
        start_date=None,
        end_date=None,
        page=1,
        page_size=10,
        current_user=user,
        db=session,
    )
    session.close()

    items = result["items"]
    subtitle_by_model = {item["model_code"]: item["subtitle"] for item in items}
    billing_mode_by_model = {item["model_code"]: item["billing_mode"] for item in items}

    assert subtitle_by_model["wan2.6-i2v-flash"] == "wan2.6-i2v-flash · 5 秒 · ¥0.7500"
    assert subtitle_by_model["qwen-image-2.0-pro"] == "qwen-image-2.0-pro · 1 张 · ¥0.5000"
    assert subtitle_by_model["qwen3-tts-vd-2026-01-26"] == "qwen3-tts-vd-2026-01-26 · 2,000 字符 · ¥0.1200"
    assert subtitle_by_model["minimax-m2.5"] == "minimax-m2.5 · 199 tokens · ¥0.0014"
    assert billing_mode_by_model["wan2.6-i2v-flash"] == "per_second"
    assert billing_mode_by_model["qwen-image-2.0-pro"] == "per_image"
    assert billing_mode_by_model["qwen3-tts-vd-2026-01-26"] == "per_10k_chars"
    assert billing_mode_by_model["minimax-m2.5"] == "token"
