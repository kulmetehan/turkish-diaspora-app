"""
FastAPI entrypoint.

Wat je hier krijgt:
- CORS (nu permissief; zet later specifieke origins).
- Startup check die de DB-verbinding verifieert (faalt hard als het misgaat).
- Eenvoudige health endpoints.

Start lokaal:
    cd "./Turkish Diaspora App/Backend"
    source .venv/bin/activate
    # Alleen als je lokaal TLS-inspectie/self-signed CA hebt:
    export SUPABASE_SSL_NO_VERIFY=1
    uvicorn app.main:app --reload
"""

import os
import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import ping_db

# -----------------------------------------------------------------------------
# App-instantie
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Turkish Diaspora Backend",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# -----------------------------------------------------------------------------
# CORS (nu open; zet later alleen je frontend(s) toe)
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # bv. ["http://localhost:5173", "https://jouwdomein.nl"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Startup: check databaseverbinding
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    try:
        await ping_db()
        print("[startup] Database OK")
    except Exception as e:
        # Faal bewust zodat je het meteen ziet bij opstarten
        print(f"[startup] Database ping failed: {e}")
        raise

# -----------------------------------------------------------------------------
# Health endpoints
# -----------------------------------------------------------------------------
@app.get("/", tags=["health"])
async def root():
    return {
        "app": "Turkish Diaspora Backend",
        "version": settings.APP_VERSION,
        "status": "running",
    }

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}

@app.get("/version", tags=["health"])
async def version():
    return {"version": settings.APP_VERSION}

@app.get("/db/ping", tags=["health"])
async def db_ping():
    # Actieve check op de DB
    await ping_db()
    return {"db": "ok"}

# -----------------------------------------------------------------------------
# Entrypoint (lokaal starten met: python -m app.main of uvicorn app.main:app)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )
