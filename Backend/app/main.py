# app/main.py
from __future__ import annotations

import sys
from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# --- NIEUW: logging bootstrap & request id middleware ------------------------
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import configure_logging, logger
from app.core.request_id import set_request_id, clear_request_id

# --- sys.path fix (root toevoegen) ---
THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parents[1]  # .../Backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Configureer uniforme logging voor de API
configure_logging(service_name="api")

app = FastAPI(
    title="Turkish Diaspora App - Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Neem bestaande X-Request-ID over of genereer er één
        req_id = request.headers.get("x-request-id") or request.headers.get("X-Request-Id")
        if not req_id:
            # korte uuid
            import uuid
            req_id = uuid.uuid4().hex
        set_request_id(req_id)
        # start log
        logger.info("request_started", method=request.method, path=str(request.url.path))
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error("request_exception", error=str(exc.__class__.__name__))
            clear_request_id()
            raise
        # end log
        logger.info("request_ended", status_code=response.status_code)
        # reflecteer request id terug naar client (handig voor tracering)
        response.headers["X-Request-Id"] = req_id
        clear_request_id()
        return response

# Middleware registreren (plaats dit NA app = FastAPI(...))
app.add_middleware(RequestIdMiddleware)

# --- CORS: dev + prod (GitHub Pages) ---
ALLOWED_ORIGINS = [
    # dev (Vite)
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    # prod (GitHub Pages)
    "https://kulmetehan.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,   # geen cookies nodig → laat False
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

# --- Universele preflight (belt & braces) ---
@app.options("/{rest_of_path:path}")
async def any_preflight(rest_of_path: str) -> Response:
    # CORSMiddleware voegt de juiste headers toe; wij geven alleen 204 terug
    return Response(status_code=204)

# --- Routers includen (indien aanwezig) ---
def _include_if_present(mod_path: str, router_attr: str = "router"):
    try:
        module = __import__(mod_path, fromlist=[router_attr])
    except ModuleNotFoundError:
        return
    router = getattr(module, router_attr, None)
    if router is not None:
        app.include_router(router)

_include_if_present("api.routers.dev_ai")
_include_if_present("api.routers.dev_classify")
_include_if_present("api.routers.google_dev")

# Locations + Admin
from api.routers.locations import router as locations_router
app.include_router(locations_router)

from api.routers import admin as admin_router
app.include_router(admin_router.router, prefix="/api/v1")