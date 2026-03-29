from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decrypt_api_key, encrypt_api_key, generate_api_key
from app.models import ApiKey, UsageLog, UsageReservation, User
from app.schemas.api_key import ApiKeyResponse, CreateApiKeyRequest, UpdateApiKeyRequest


def create_api_key(user: User, payload: CreateApiKeyRequest, db: Session) -> tuple[ApiKey, str]:
    plaintext_key, key_prefix, key_hash = generate_api_key()
    entity = ApiKey(
        user_id=user.id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        encrypted_key=encrypt_api_key(plaintext_key),
        token_limit=payload.token_limit,
        request_limit=payload.request_limit,
        budget_limit=payload.budget_limit,
        status="active",
        used_amount=Decimal("0.0000"),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity, plaintext_key


def update_api_key(api_key: ApiKey, payload: UpdateApiKeyRequest, db: Session) -> ApiKey:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)
    db.commit()
    db.refresh(api_key)
    return api_key


def ensure_key_belongs_to_user(key_id: int, user: User, db: Session) -> ApiKey:
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.user_id == user.id).first()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    return api_key


def delete_api_key(api_key: ApiKey, db: Session) -> None:
    pending_reservation = (
        db.query(UsageReservation)
        .filter(UsageReservation.api_key_id == api_key.id, UsageReservation.status == "pending")
        .first()
    )
    if pending_reservation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该 API Key 还有进行中的请求，暂时不能删除",
        )

    (
        db.query(UsageLog)
        .filter(UsageLog.api_key_id == api_key.id)
        .update({UsageLog.api_key_id: None}, synchronize_session=False)
    )
    db.query(UsageReservation).filter(UsageReservation.api_key_id == api_key.id).delete(
        synchronize_session=False,
    )
    db.delete(api_key)
    db.commit()


def get_api_key_plaintext(api_key: ApiKey) -> str:
    if not api_key.encrypted_key:
        return ""
    try:
        return decrypt_api_key(api_key.encrypted_key)
    except Exception:
        return ""


def build_api_key_response(api_key: ApiKey, db: Session, plaintext_key: str | None = None) -> ApiKeyResponse:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    logs = db.query(UsageLog).filter(UsageLog.api_key_id == api_key.id).all()
    month_requests = sum(1 for log in logs if log.created_at and log.created_at >= month_start)
    total_requests = len(logs)
    success_count = sum(1 for log in logs if log.status == "success")
    success_rate = Decimal("100.00")
    if total_requests:
        success_rate = (Decimal(success_count) / Decimal(total_requests) * Decimal("100")).quantize(
            Decimal("0.01")
        )
    latencies = [log.response_time_ms for log in logs if log.response_time_ms]
    avg_response_time_ms = round(sum(latencies) / len(latencies)) if latencies else None

    return ApiKeyResponse(
        **ApiKeyResponse.model_validate(api_key).model_dump(
            exclude={"plaintext_key", "month_requests", "success_rate", "avg_response_time_ms"}
        ),
        plaintext_key=plaintext_key,
        month_requests=month_requests,
        success_rate=success_rate,
        avg_response_time_ms=avg_response_time_ms,
    )
