from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import ApiKey, ModelCatalog, ModelPriceSnapshot, RefundRequest, User, WalletAccount


MODEL_SEEDS = [
    {
        "provider": "alibaba-bailian",
        "model_code": "qwen-plus",
        "model_id": "qwen-plus",
        "capability_type": "chat",
        "display_name": "Qwen3.5 27B",
        "vendor_display_name": "Alibaba",
        "category": "text",
        "billing_mode": "token",
        "pricing_items": '[{"label":"输入","unit":"元/百万Token","price":"0.8"},{"label":"输出","unit":"元/百万Token","price":"4.8"}]',
        "input_price_per_million": Decimal("0.80"),
        "output_price_per_million": Decimal("4.80"),
        "price_source": "official_doc",
        "last_price_synced_at": datetime.now(timezone.utc),
        "description": "强大的多模态AI模型，支持文本和图像处理",
        "hero_description": "强大的多模态AI模型，支持文本和图像处理",
        "rating": Decimal("4.80"),
        "support_features": "多轮对话,代码生成,文本分析,翻译",
        "tags": "多轮对话,代码生成,文本分析,翻译",
        "example_python": "",
        "example_typescript": "",
        "example_curl": "",
    },
    {
        "provider": "alibaba-bailian",
        "model_code": "qwen-turbo",
        "model_id": "qwen-turbo",
        "capability_type": "chat",
        "display_name": "Qwen Turbo",
        "vendor_display_name": "Alibaba",
        "category": "text",
        "billing_mode": "token",
        "pricing_items": '[{"label":"输入","unit":"元/百万Token","price":"1.5"},{"label":"输出","unit":"元/百万Token","price":"3"}]',
        "input_price_per_million": Decimal("1.50"),
        "output_price_per_million": Decimal("3.00"),
        "price_source": "seed",
        "last_price_synced_at": datetime.now(timezone.utc),
        "description": "低延迟低成本模型，适合高频调用与轻量场景",
        "hero_description": "低延迟低成本模型，适合高频调用与轻量场景",
        "rating": Decimal("4.70"),
        "support_features": "多轮对话,高并发,快速响应,翻译",
        "tags": "快速响应,低成本,高并发,翻译",
        "example_python": "",
        "example_typescript": "",
        "example_curl": "",
    },
    {
        "provider": "alibaba-bailian",
        "model_code": "qwen-max",
        "model_id": "qwen-max-latest",
        "capability_type": "chat",
        "display_name": "Qwen Max",
        "vendor_display_name": "Alibaba",
        "category": "text",
        "billing_mode": "token",
        "pricing_items": '[{"label":"输入","unit":"元/百万Token","price":"12"},{"label":"输出","unit":"元/百万Token","price":"36"}]',
        "input_price_per_million": Decimal("12.00"),
        "output_price_per_million": Decimal("36.00"),
        "price_source": "seed",
        "last_price_synced_at": datetime.now(timezone.utc),
        "description": "旗舰模型，适用于复杂推理、生成和高质量问答",
        "hero_description": "旗舰模型，适用于复杂推理、生成和高质量问答",
        "rating": Decimal("4.90"),
        "support_features": "复杂推理,多轮对话,代码生成,办公助手",
        "tags": "复杂推理,旗舰模型,办公助手",
        "example_python": "",
        "example_typescript": "",
        "example_curl": "",
    },
]


def seed_models(db: Session):
    existing_rows = {
        row.model_code: row
        for row in db.query(ModelCatalog).all()
    }
    for item in MODEL_SEEDS:
        existing = existing_rows.get(item["model_code"])
        if existing:
            existing.provider = item["provider"]
            existing.display_name = item["display_name"]
            existing.category = item["category"]
            existing.billing_mode = item["billing_mode"]
            existing.pricing_items = item["pricing_items"]
            existing.input_price_per_million = item["input_price_per_million"]
            existing.output_price_per_million = item["output_price_per_million"]
            existing.price_source = item["price_source"]
            existing.last_price_synced_at = item["last_price_synced_at"]
            existing.description = item["description"]
            existing.is_active = True
            existing.model_id = item["model_id"]
            existing.capability_type = item.get("capability_type", "chat")
            existing.vendor_display_name = item["vendor_display_name"]
            existing.rating = item["rating"]
            existing.hero_description = item["hero_description"]
            existing.support_features = item["support_features"]
            existing.tags = item["tags"]
            existing.example_python = item["example_python"]
            existing.example_typescript = item["example_typescript"]
            existing.example_curl = item["example_curl"]
            continue
        db.add(ModelCatalog(**item))


def backfill_model_price_snapshots(db: Session):
    models = db.query(ModelCatalog).all()
    for model in models:
        exists = db.query(ModelPriceSnapshot.id).filter(ModelPriceSnapshot.model_catalog_id == model.id).first()
        if exists:
            continue
        db.add(
            ModelPriceSnapshot(
                model_catalog_id=model.id,
                input_price_per_million=model.input_price_per_million,
                output_price_per_million=model.output_price_per_million,
                price_source=model.price_source or "seed",
                note="系统初始化价格基线",
            )
        )


def seed_admin(db: Session):
    admin = db.query(User).filter(User.email == settings.admin_email).first()
    if admin:
        if not admin.phone:
            admin.phone = "13800000000"
        return

    admin = User(
        email=settings.admin_email,
        phone="13800000000",
        password_hash=hash_password(settings.admin_password),
        name="管理员",
        role="admin",
        status="active",
    )
    db.add(admin)
    db.flush()
    db.add(WalletAccount(user_id=admin.id, balance=Decimal("9999.0000"), currency="CNY"))


def initialize_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        wallet_columns = {column["name"] for column in inspector.get_columns("wallet_accounts")}
        if "reserved_balance" not in wallet_columns:
            db.execute(
                text(
                    "ALTER TABLE wallet_accounts "
                    "ADD COLUMN reserved_balance NUMERIC(18,4) NOT NULL DEFAULT 0.0000"
                )
            )
            db.commit()
        api_key_columns = {column["name"] for column in inspector.get_columns("api_keys")}
        if "encrypted_key" not in api_key_columns:
            db.execute(
                text(
                    "ALTER TABLE api_keys "
                    "ADD COLUMN encrypted_key VARCHAR(255) NOT NULL DEFAULT ''"
                )
            )
            db.commit()
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "phone" not in user_columns:
            db.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(32)"))
            db.commit()
        db.execute(text("UPDATE users SET phone = '13800000000' WHERE email = :email AND (phone IS NULL OR phone = '')"), {"email": settings.admin_email})
        db.commit()
        model_columns = {column["name"] for column in inspector.get_columns("model_catalog")}
        if "model_id" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN model_id VARCHAR(160) NOT NULL DEFAULT ''"))
            db.commit()
        if "capability_type" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN capability_type VARCHAR(32) NOT NULL DEFAULT 'chat'"))
            db.commit()
        if "vendor_display_name" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN vendor_display_name VARCHAR(120) NOT NULL DEFAULT ''"))
            db.commit()
        if "price_source" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN price_source VARCHAR(32) NOT NULL DEFAULT 'manual'"))
            db.commit()
        if "billing_mode" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN billing_mode VARCHAR(32) NOT NULL DEFAULT 'token'"))
            db.commit()
        if "pricing_items" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN pricing_items TEXT NOT NULL DEFAULT '[]'"))
            db.commit()
        if "last_price_synced_at" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN last_price_synced_at TIMESTAMP WITH TIME ZONE"))
            db.commit()
        if "rating" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN rating NUMERIC(4,2) NOT NULL DEFAULT 4.80"))
            db.commit()
        if "hero_description" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN hero_description TEXT NOT NULL DEFAULT ''"))
            db.commit()
        if "support_features" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN support_features TEXT NOT NULL DEFAULT ''"))
            db.commit()
        if "tags" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN tags TEXT NOT NULL DEFAULT ''"))
            db.commit()
        if "example_python" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN example_python TEXT NOT NULL DEFAULT ''"))
            db.commit()
        if "example_typescript" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN example_typescript TEXT NOT NULL DEFAULT ''"))
            db.commit()
        if "example_curl" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN example_curl TEXT NOT NULL DEFAULT ''"))
            db.commit()
        if "sync_status" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN sync_status VARCHAR(32) NOT NULL DEFAULT 'pending'"))
            db.commit()
        if "sync_error" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN sync_error TEXT NOT NULL DEFAULT ''"))
            db.commit()
        bailian_cache_columns = {column["name"] for column in inspector.get_columns("bailian_model_cache")}
        if "billing_mode" not in bailian_cache_columns:
            db.execute(text("ALTER TABLE bailian_model_cache ADD COLUMN billing_mode VARCHAR(32) NOT NULL DEFAULT 'token'"))
            db.commit()
        if "pricing_items" not in bailian_cache_columns:
            db.execute(text("ALTER TABLE bailian_model_cache ADD COLUMN pricing_items TEXT NOT NULL DEFAULT '[]'"))
            db.commit()
        usage_log_columns = {column["name"] for column in inspector.get_columns("usage_logs")}
        if "response_time_ms" not in usage_log_columns:
            db.execute(text("ALTER TABLE usage_logs ADD COLUMN response_time_ms INTEGER"))
            db.commit()
        payment_order_columns = {column["name"] for column in inspector.get_columns("payment_orders")}
        if "channel_order_no" not in payment_order_columns:
            db.execute(text("ALTER TABLE payment_orders ADD COLUMN channel_order_no VARCHAR(128)"))
            db.commit()
        if "payment_url" not in payment_order_columns:
            db.execute(text("ALTER TABLE payment_orders ADD COLUMN payment_url VARCHAR(2000)"))
            db.commit()
        if "qr_code" not in payment_order_columns:
            db.execute(text("ALTER TABLE payment_orders ADD COLUMN qr_code VARCHAR(2000)"))
            db.commit()
        if "qr_code_image" not in payment_order_columns:
            db.execute(text("ALTER TABLE payment_orders ADD COLUMN qr_code_image VARCHAR(5000)"))
            db.commit()
        seed_models(db)
        seed_admin(db)
        backfill_model_price_snapshots(db)
        db.commit()
    finally:
        db.close()
