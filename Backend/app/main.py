# app/main.py
from __future__ import annotations
import sys
from pathlib import Path
from fastapi import FastAPI

# Zorg dat de projectroot (map met 'app', 'api', 'services') op sys.path staat
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]  # .../Backend
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(
    title="Turkish Diaspora App - Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.get("/")
async def root():
    return {"ok": True, "app": "TDA Backend", "message": "Up & running"}

@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}

def _import_dev_classify_router():
    try:
        from app.api.routers import dev_classify as dev_classify_router
        return dev_classify_router
    except ModuleNotFoundError:
        pass
    try:
        from api.routers import dev_classify as dev_classify_router
        return dev_classify_router
    except ModuleNotFoundError:
        return None

_dev_router = _import_dev_classify_router()
if _dev_router is not None:
    app.include_router(_dev_router.router)
else:
    @app.get("/dev/ai/_missing")
    async def dev_router_missing():
        return {
            "ok": False,
            "hint": "dev_classify router not found. Ensure dev_classify.py exists and __init__.py files are present."
        }
