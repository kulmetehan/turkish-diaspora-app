# Backend/app/main.py
from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# --- Logging & request-id ---
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

from app.core.logging import configure_logging, logger
from app.core.request_id import set_request_id, clear_request_id
from services.db_service import init_db_pool

# Routers (import APIRouter instances directly)
from api.routers.locations import router as locations_router
from api.routers.dev_classify import router as dev_classify_router
try:
    from api.routers.dev_ai import router as dev_ai_router  # optional, may not exist
except Exception:
    dev_ai_router = None  # type: ignore
from api.routers.admin import router as admin_router
from api.routers.admin_auth import router as admin_auth_router
from api.routers.admin_locations import router as admin_locations_router

# --- sys.path fix (root toevoegen) ---
THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parents[1]  # .../Backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Configureer logging voor de API
configure_logging(service_name="api")

app = FastAPI(
    title="Turkish Diaspora App - Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.on_event("startup")
async def _startup_db_pool() -> None:
    await init_db_pool()

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or request.headers.get("X-Request-Id")
        if not req_id:
            import uuid
            req_id = uuid.uuid4().hex
        set_request_id(req_id)
        logger.info("request_started", method=request.method, path=str(request.url.path))
        try:
            response: StarletteResponse = await call_next(request)
        except Exception as exc:
            logger.error("request_exception", error=str(exc.__class__.__name__))
            clear_request_id()
            raise
        logger.info("request_ended", status_code=response.status_code)
        response.headers["X-Request-Id"] = req_id
        clear_request_id()
        return response

app.add_middleware(RequestIdMiddleware)

# --- CORS ---
ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:5174", "http://127.0.0.1:5174",
    "https://kulmetehan.github.io",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health endpoints ---
@app.get("/")
async def root():
    return {"ok": True, "app": "TDA Backend", "message": "Up & running"}

@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}

@app.get("/health")
async def health():
    return {"ok": True}

# --- Universele preflight ---
@app.options("/{rest_of_path:path}")
async def any_preflight(rest_of_path: str) -> Response:
    return Response(status_code=204)

# --- Routers includen (direct) ---
app.include_router(locations_router)
app.include_router(dev_classify_router)
if dev_ai_router is not None:
    app.include_router(dev_ai_router)
app.include_router(admin_router)
app.include_router(admin_auth_router)
app.include_router(admin_locations_router)

logger.info("routers_registered", routers=["locations", "dev_classify", "dev_ai", "admin", "admin_auth", "admin_locations"])
