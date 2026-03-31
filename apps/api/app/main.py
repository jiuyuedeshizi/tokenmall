from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler

from app.api.admin import router as admin_router
from app.api.api_keys import router as api_keys_router
from app.api.auth import router as auth_router
from app.api.bailian_native import router as bailian_native_router
from app.api.dashboard import router as dashboard_router
from app.api.models import router as models_router
from app.api.payments import router as payments_router
from app.api.proxy import router as proxy_router
from app.api.usage import router as usage_router
from app.api.wallet import router as wallet_router
from app.core.config import settings
from app.db.init_db import initialize_database
from app.services.proxy import build_openai_error_response, openai_error_from_http_exception

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
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
app.include_router(bailian_native_router, tags=["bailian-native"])


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_wrapper(request: Request, exc: HTTPException):
    if request.url.path.startswith("/v1/"):
        return openai_error_from_http_exception(exc)
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_wrapper(request: Request, exc: Exception):  # noqa: ARG001
    if request.url.path.startswith("/v1/"):
        logger.exception("Unhandled proxy error")
        return build_openai_error_response(
            status_code=500,
            message="Internal server error",
            error_type="server_error",
        )
    logger.exception("Unhandled application error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
