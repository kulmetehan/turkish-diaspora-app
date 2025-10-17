# app/main.py
from __future__ import annotations

import sys
from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# --- sys.path fix (root toevoegen) ---
THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parents[1]  # .../Backend
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

app = FastAPI(
    title="Turkish Diaspora App - Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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
