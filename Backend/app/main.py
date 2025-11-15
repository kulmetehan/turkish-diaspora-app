# Backend/app/main.py
from __future__ import annotations

# --- ensure project root is on sys.path so `api.*` and `app.*` are both importable ---
import sys
from pathlib import Path
THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parents[1]  # .../Backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
# -------------------------------------------------------------------------

from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
from fastapi import FastAPI, Response, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# --- Logging & request-id ---
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

from typing import Dict, Optional

from app.core.logging import configure_logging, logger
from app.core.request_id import set_request_id, clear_request_id
from services.db_service import init_db_pool
from app.core.db_monitor import DbSessionMonitor

# Routers from the top-level `api/routers` package:
from api.routers.locations import router as locations_router
from api.routers.dev_classify import router as dev_classify_router
try:
    from api.routers.dev_ai import router as dev_ai_router  # optional, may not exist
except Exception:
    dev_ai_router = None  # type: ignore
from api.routers.admin import router as admin_router
from api.routers.admin_auth import router as admin_auth_router
from api.routers.admin_locations import router as admin_locations_router
from api.routers.admin_misc import router as admin_misc_router
from api.routers.admin_metrics import router as admin_metrics_router
from api.routers.admin_discovery import router as admin_discovery_router
from api.routers.admin_workers import router as admin_workers_router
from api.routers.admin_ai_logs import router as admin_ai_logs_router
from api.routers.admin_ai_config import router as admin_ai_config_router
from api.routers.admin_tasks import router as admin_tasks_router

# Import path prepared above for both `api.*` and `app.*`

# Configureer logging voor de API
configure_logging(service_name="api")

app = FastAPI(
    title="Turkish Diaspora App - Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

db_session_monitor = DbSessionMonitor()

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def _cors_headers(origin: Optional[str]) -> Dict[str, str]:
    if origin and origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return {}

@app.on_event("startup")
async def _startup_db_pool() -> None:
    await init_db_pool()
    db_session_monitor.start()

@app.on_event("shutdown")
async def _shutdown_cleanup() -> None:
    await db_session_monitor.stop()

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or request.headers.get("X-Request-Id")
        if not req_id:
            import uuid
            req_id = uuid.uuid4().hex
        set_request_id(req_id)
        
        # Log Origin header for CORS debugging (debug level for /api/v1/locations endpoints)
        origin = request.headers.get("origin") or request.headers.get("Origin")
        if origin and ("/api/v1/locations" in str(request.url.path)):
            logger.debug("request_origin", origin=origin, path=str(request.url.path))
        
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

# --- CORS ---
# CORS must be added FIRST to be outermost middleware.
# In Starlette/FastAPI, middleware executes in reverse order:
# - First added = outermost (executes last on requests, first on responses)
# - Last added = innermost (executes first on requests, last on responses)
# Being outermost ensures CORS headers are added to all responses first.
# CORSMiddleware handles preflight OPTIONS requests correctly regardless of order.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://kulmetehan.github.io",
        "https://turkish-diaspora-app.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["Content-Length"],
)

# Add RequestIdMiddleware after CORS (will be innermost, executes first on requests)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    origin = request.headers.get("origin") or request.headers.get("Origin")
    headers = dict(exc.headers or {})
    headers.update(_cors_headers(origin))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    origin = request.headers.get("origin") or request.headers.get("Origin")
    headers = _cors_headers(origin)
    logger.exception("unhandled_exception", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"}, headers=headers)

# --- Health endpoints ---
@app.get("/")
async def root():
    return {"ok": True, "app": "TDA Backend", "message": "Up & running"}

@app.head("/")
async def root_head():
    """HEAD handler for root endpoint to avoid 405 errors in logs."""
    return Response(status_code=200)

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

# --- API v1 router ---
# Centralize public/external API routes under a single versioned router.
# This guarantees that e.g. GET /api/v1/admin/locations maps to list_admin_locations.
api_v1_router = APIRouter(prefix="/api/v1")

# Debug-only endpoint to verify that the versioned router is active in production.
# Safe to remove after verifying Render serves the new router structure.
@api_v1_router.get("/_whoami")
async def whoami():
    # This route exists ONLY for debugging prod deployment/version and can be removed later.
    return {
        "ok": True,
        "router_mode": "api_v1_enabled",
        "note": "If you can see this in prod at /api/v1/_whoami, Render is serving the new router structure.",
    }

# Routers that are externally consumed by frontend/clients
api_v1_router.include_router(locations_router)
api_v1_router.include_router(admin_auth_router)
api_v1_router.include_router(admin_locations_router)
api_v1_router.include_router(admin_misc_router)
api_v1_router.include_router(admin_metrics_router)
api_v1_router.include_router(admin_discovery_router)
api_v1_router.include_router(admin_workers_router)
api_v1_router.include_router(admin_ai_logs_router)
api_v1_router.include_router(admin_ai_config_router)
api_v1_router.include_router(admin_tasks_router)

# Mount the versioned API once on the app
app.include_router(api_v1_router)

# Keep dev/local-only routers mounted at top-level (not versioned)
app.include_router(dev_classify_router)
if dev_ai_router is not None:
    app.include_router(dev_ai_router)
app.include_router(admin_router)

logger.info("routers_registered", routers=["api_v1(locations,admin_auth,admin_locations,admin_misc,admin_metrics)", "dev_classify", "dev_ai", "admin"])