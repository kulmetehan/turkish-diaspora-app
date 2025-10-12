import os
import json
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import google_dev

from app.config import settings
from app.db import ping_db

# ----------------------------------------------------
# Logging setup
# ----------------------------------------------------
logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------
# App setup
# ----------------------------------------------------
app = FastAPI(
    title="Turkish Diaspora Backend",
    version=getattr(settings, "APP_VERSION", "0.1.0"),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Routers registreren
app.include_router(google_dev.router)

# ----------------------------------------------------
# CORS
# ----------------------------------------------------
# Gebruik lijst uit settings als die bestaat; anders veilige defaults
default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
cors_origins = (
    getattr(settings, "CORS_ORIGINS", None)
    or getattr(settings, "FRONTEND_ORIGINS", None)
    or default_cors_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# Lifecycle hooks
# ----------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    # Probeer DB te pingen bij start-up (handig voor snelle diagnose)
    try:
        logger.info(json.dumps({"event": "Checking database connection...", "logger": "api"}))
        await ping_db()
        logger.info(json.dumps({"event": "Database connection OK.", "logger": "api"}))
    except Exception as exc:
        # We laten de app wel starten; frontend kan nog steeds draaien
        logger.error(
            json.dumps(
                {
                    "event": "Database connection failed.",
                    "error": str(exc),
                    "logger": "api",
                }
            )
        )

# ----------------------------------------------------
# Routes
# ----------------------------------------------------
@app.get("/health", tags=["health"])
def health():
    """
    Eenvoudige healthcheck voor de frontend.
    """
    return {
        "status": "ok",
        "version": getattr(settings, "APP_VERSION", "0.1.0"),
    }

@app.get("/version", tags=["health"])
def version():
    return {"version": getattr(settings, "APP_VERSION", "0.1.0")}

@app.get("/db/ping", tags=["health"])
async def db_ping():
    await ping_db()
    return {"db": "ok"}

# ----------------------------------------------------
# Local dev entrypoint
# ----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 8000)),
        reload=True,
    )