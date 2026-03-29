from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ApiKey
from app.schemas.api_key import ApiKeyResponse, CreateApiKeyRequest, UpdateApiKeyRequest
from app.services.api_keys import (
    build_api_key_response,
    create_api_key,
    delete_api_key as delete_api_key_service,
    ensure_key_belongs_to_user,
    get_api_key_plaintext,
    update_api_key,
)

router = APIRouter()


@router.get("", response_model=list[ApiKeyResponse])
def list_api_keys(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [
        build_api_key_response(item, db, get_api_key_plaintext(item) or None)
        for item in items
    ]


@router.post("", response_model=ApiKeyResponse)
def create_api_key_endpoint(
    payload: CreateApiKeyRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key, plaintext_key = create_api_key(current_user, payload, db)
    return build_api_key_response(api_key, db, plaintext_key)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
def update_api_key_endpoint(
    key_id: int,
    payload: UpdateApiKeyRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = ensure_key_belongs_to_user(key_id, current_user, db)
    api_key = update_api_key(api_key, payload, db)
    return build_api_key_response(api_key, db, get_api_key_plaintext(api_key) or None)


@router.post("/{key_id}/disable", response_model=ApiKeyResponse)
def disable_api_key(key_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    api_key = ensure_key_belongs_to_user(key_id, current_user, db)
    api_key.status = "disabled"
    db.commit()
    db.refresh(api_key)
    return build_api_key_response(api_key, db, get_api_key_plaintext(api_key) or None)


@router.post("/{key_id}/enable", response_model=ApiKeyResponse)
def enable_api_key(key_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    api_key = ensure_key_belongs_to_user(key_id, current_user, db)
    api_key.status = "active"
    db.commit()
    db.refresh(api_key)
    return build_api_key_response(api_key, db, get_api_key_plaintext(api_key) or None)


@router.delete("/{key_id}")
def delete_api_key(key_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    api_key = ensure_key_belongs_to_user(key_id, current_user, db)
    delete_api_key_service(api_key, db)
    return {"success": True}
