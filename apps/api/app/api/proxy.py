from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_api_key_entity
from app.db.session import get_db
from app.models import User
from app.services.proxy import proxy_chat_completion

router = APIRouter()


@router.post("/chat/completions")
async def create_chat_completion(
    payload: dict = Body(...),
    api_key=Depends(get_api_key_entity),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == api_key.user_id).first()
    return await proxy_chat_completion(api_key, user, payload, db)
