# app/main.py
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Let op: jouw routers staan in het top-level package 'api'
from api.routers import dev_ai  # zorg dat api/__init__.py en api/routers/__init__.py bestaan

# Config (laadt .env via app/config.py)
from app.config import settings

logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

app = FastAPI(
    title="Turkish Diaspora App API",
    version=settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "0.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — pas origin(s) aan naar wens
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # voeg hier evt. je productiedomeinen toe
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Global exception handlers
# =========================
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": "internal_error",
            "detail": "An unexpected error occurred.",
        },
    )

# ==========
# Health APIs
# ==========
@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "ok": True,
        "name": "Turkish Diaspora App API",
        "version": settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "0.0.0",
    }

@app.get("/health")
@app.get("/healthz")
def health() -> Dict[str, Any]:
    return {"ok": True}

@app.get("/readyz")
def readyz() -> Dict[str, Any]:
    # Eventueel checks toevoegen (DB ping, queue, etc.)
    return {"ok": True, "ready": True}

# ===========
# Include APIs
# ===========
app.include_router(dev_ai.router)

# Optioneel: alleen includen als aanwezig; stoort niet als ontbreekt.
try:
    from api.routers import google_dev  # type: ignore
    app.include_router(google_dev.router)
except Exception:
    logger.info("google_dev router not found; skipping.")
