# app/main.py
from __future__ import annotations

import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Zorg dat de Backend-root altijd op sys.path staat (i.v.m. spaties e.d.) ---
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

# --- CORS (dev) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
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

# === Include bestaande DEV routers (alleen als ze bestaan) ===
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

# === Include LOCATIONS router (cruciaal) ===
# NB: De router heeft zélf prefix="/api/v1/locations" — geen extra prefix hier.
from api.routers.locations import router as locations_router
app.include_router(locations_router)
