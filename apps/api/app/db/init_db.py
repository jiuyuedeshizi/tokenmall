from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import ModelCatalog, User, WalletAccount
from app.services.official_model_catalog import OFFICIAL_MODEL_CATALOG


def seed_official_model_catalog(db: Session):
    if db.query(ModelCatalog.id).first():
        return

    for model_code, item in OFFICIAL_MODEL_CATALOG.items():
        upstream_model_id = item.get("upstream_model_id", model_code)
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
        seed_official_model_catalog(db)
        seed_admin(db)
        db.commit()
    finally:
        db.close()
