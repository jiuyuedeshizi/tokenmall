from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.api_keys import router as api_keys_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.models import router as models_router
from app.api.payments import router as payments_router
from app.api.proxy import router as proxy_router
from app.api.usage import router as usage_router
from app.api.wallet import router as wallet_router
from app.core.config import settings
from app.db.init_db import initialize_database
from app.services.litellm_models import sync_active_models_to_litellm

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    try:
        sync_active_models_to_litellm()
    except Exception as exc:  # noqa: BLE001
        logger.warning("LiteLLM 模型自动同步失败：%s", exc)
    yield


app = FastAPI(title="TokenMall API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(models_router, prefix="/models", tags=["models"])
app.include_router(wallet_router, prefix="/wallet", tags=["wallet"])
app.include_router(payments_router, prefix="/payments", tags=["payments"])
app.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])
app.include_router(usage_router, prefix="/usage", tags=["usage"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(proxy_router, prefix="/v1", tags=["proxy"])


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
