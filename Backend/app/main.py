import logging
import sys
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .core.config import settings

# --- 1. Structured Logging Configuration (Same as before) ---
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
formatter = structlog.stdlib.ProcessorFormatter(
    processor=structlog.processors.JSONRenderer(),
)
root_logger = logging.getLogger()
if root_logger.handlers:
    root_logger.handlers[0].setFormatter(formatter)
else:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

log = structlog.get_logger("api")


# --- 2. Create The FastAPI App Instance ---
# THIS MUST BE CREATED BEFORE IT CAN BE USED BY THE MIDDLEWARE
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.APP_VERSION,
)


# --- 3. Middleware for Request IDs ---
# NOW we can attach the middleware using the correct `app` object
@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """
    Adds a unique X-Request-ID header to every request and response.
    """
    request_id = str(uuid.uuid4())
    logger = log.bind(request_id=request_id)

    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path
    )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_finished",
        status_code=response.status_code
    )
    return response


# --- 4. API Endpoints (Same as before) ---
@app.get("/health", tags=["Monitoring"])
def get_health() -> dict[str, str]:
    """
    Health check endpoint to confirm the API is running.
    """
    log.info("Health check endpoint was called")
    return {"status": "ok"}


@app.get("/version", tags=["Monitoring"])
def get_version() -> dict[str, str]:
    """
    Returns the current version of the application from settings.
    """
    return {"version": settings.APP_VERSION}