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

# --- Routers includen ---
def _include_if_present(mod_path: str, router_attr: str = "router") -> bool:
    try:
        module = __import__(mod_path, fromlist=[router_attr])
    except ModuleNotFoundError:
        logger.info("router_missing", module=mod_path)
        return False
    router = getattr(module, router_attr, None)
    if router is not None:
        app.include_router(router)
        logger.info("router_included", module=mod_path)
        return True
    logger.info("router_attr_missing", module=mod_path)
    return False

# Dev/utility routers
_include_if_present("api.routers.dev_ai")
_include_if_present("api.routers.dev_classify")
_include_if_present("api.routers.google_dev")  # <-- belangrijk voor /dev/google/nearby

# Locations + Admin
try:
    from api.routers.locations import router as locations_router
    app.include_router(locations_router)
    logger.info("router_included", module="api.routers.locations")
except ModuleNotFoundError:
    logger.info("router_missing", module="api.routers.locations")

try:
    from api.routers import admin as admin_router
    app.include_router(admin_router.router, prefix="/api/v1")
    logger.info("router_included", module="api.routers.admin")
except ModuleNotFoundError:
    logger.info("router_missing", module="api.routers.admin")
