from decimal import Decimal

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import ApiKey, BailianModelCache, ModelCatalog, ModelPriceSnapshot, RefundRequest, User, WalletAccount
from app.services.official_model_catalog import OFFICIAL_MODEL_CATALOG

def sync_official_model_catalog(db: Session):
    existing_models = {row.model_code: row for row in db.query(ModelCatalog).all()}
    for model_code, item in OFFICIAL_MODEL_CATALOG.items():
        upstream_model_id = item.get("upstream_model_id", model_code)
        existing = existing_models.get(model_code)
        if existing:
            existing.provider = item["provider"]
            existing.model_id = upstream_model_id
            existing.capability_type = item["capability_type"]
            existing.display_name = item["display_name"]
            existing.vendor_display_name = item["vendor_display_name"]
            existing.category = item["category"]
            existing.description = item["description"]
            existing.hero_description = item["hero_description"]
            existing.support_features = item["support_features"]
            existing.tags = item["tags"]
            continue

        db.add(
            ModelCatalog(
                provider=item["provider"],
                model_code=model_code,
                model_id=upstream_model_id,
                capability_type=item["capability_type"],
                display_name=item["display_name"],
                vendor_display_name=item["vendor_display_name"],
                category=item["category"],
                billing_mode=item["billing_mode"],
                pricing_items=item["pricing_items"],
                input_price_per_million=item["input_price_per_million"],
                output_price_per_million=item["output_price_per_million"],
                description=item["description"],
                hero_description=item["hero_description"],
                rating=Decimal("4.80"),
                support_features=item["support_features"],
                tags=item["tags"],
                example_python="",
                example_typescript="",
                example_curl="",
                is_active=True,
            )
        )

    existing_cache = {
        row.upstream_model_id.lower(): row
        for row in db.query(BailianModelCache).all()
    }
    for model_code, item in OFFICIAL_MODEL_CATALOG.items():
        cache_item = existing_cache.get(model_code.lower())
        if not cache_item:
            continue
        cache_item.display_name = item["display_name"]
        cache_item.provider = item["provider"]
        cache_item.vendor_display_name = item["vendor_display_name"]
        cache_item.category = item["category"]
        cache_item.capability_type = item["capability_type"]
        cache_item.description = item["description"]
        cache_item.tags = item["tags"]
        cache_item.support_features = item["support_features"]
        cache_item.billing_mode = item["billing_mode"]
        cache_item.pricing_items = item["pricing_items"]
        cache_item.input_price_per_million = item["input_price_per_million"]
        cache_item.output_price_per_million = item["output_price_per_million"]

def prune_to_official_models(db: Session):
    official_codes = set(OFFICIAL_MODEL_CATALOG.keys())
    (
        db.query(ModelCatalog)
        .filter(~ModelCatalog.model_code.in_(official_codes))
        .delete(synchronize_session=False)
    )
    db.query(ModelPriceSnapshot).delete(synchronize_session=False)
    db.query(BailianModelCache).delete(synchronize_session=False)


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
        if "price_source" in model_columns:
            db.execute(text("ALTER TABLE model_catalog DROP COLUMN price_source"))
            db.commit()
        if "billing_mode" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN billing_mode VARCHAR(32) NOT NULL DEFAULT 'token'"))
            db.commit()
        if "pricing_items" not in model_columns:
            db.execute(text("ALTER TABLE model_catalog ADD COLUMN pricing_items TEXT NOT NULL DEFAULT '[]'"))
            db.commit()
        if "last_price_synced_at" in model_columns:
            db.execute(text("ALTER TABLE model_catalog DROP COLUMN last_price_synced_at"))
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
        if "sync_status" in model_columns:
            db.execute(text("ALTER TABLE model_catalog DROP COLUMN sync_status"))
            db.commit()
        if "sync_error" in model_columns:
            db.execute(text("ALTER TABLE model_catalog DROP COLUMN sync_error"))
            db.commit()
        bailian_cache_columns = {column["name"] for column in inspector.get_columns("bailian_model_cache")}
        if "billing_mode" not in bailian_cache_columns:
            db.execute(text("ALTER TABLE bailian_model_cache ADD COLUMN billing_mode VARCHAR(32) NOT NULL DEFAULT 'token'"))
            db.commit()
        if "pricing_items" not in bailian_cache_columns:
            db.execute(text("ALTER TABLE bailian_model_cache ADD COLUMN pricing_items TEXT NOT NULL DEFAULT '[]'"))
            db.commit()
        if "price_source" in bailian_cache_columns:
            db.execute(text("ALTER TABLE bailian_model_cache DROP COLUMN price_source"))
            db.commit()
        snapshot_columns = {column["name"] for column in inspector.get_columns("model_price_snapshots")}
        if "price_source" in snapshot_columns:
            db.execute(text("ALTER TABLE model_price_snapshots DROP COLUMN price_source"))
            db.commit()
        usage_log_columns = {column["name"] for column in inspector.get_columns("usage_logs")}
        if "response_time_ms" not in usage_log_columns:
            db.execute(text("ALTER TABLE usage_logs ADD COLUMN response_time_ms INTEGER"))
            db.commit()
        if "billing_source" not in usage_log_columns:
            db.execute(text("ALTER TABLE usage_logs ADD COLUMN billing_source VARCHAR(32) NOT NULL DEFAULT ''"))
            db.commit()
        reservation_columns = {column["name"] for column in inspector.get_columns("usage_reservations")}
        if "billing_source" not in reservation_columns:
            db.execute(text("ALTER TABLE usage_reservations ADD COLUMN billing_source VARCHAR(32) NOT NULL DEFAULT ''"))
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
        sync_official_model_catalog(db)
        prune_to_official_models(db)
        seed_admin(db)
        db.commit()
    finally:
        db.close()
