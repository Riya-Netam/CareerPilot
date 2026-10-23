import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db.session import SessionLocal
from app.services.taxonomy_store import reload_taxonomy, seed_taxonomy

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("careerpilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables come from Alembic migrations (alembic upgrade head). Seeding is idempotent.
    try:
        with SessionLocal() as db:
            seed_taxonomy(db)
            reload_taxonomy(db)
    except Exception as e:
        log.error("Startup seeding skipped (is the database migrated?): %s", type(e).__name__)
    yield


app = FastAPI(title="CareerPilot AI API", version="1.0.0", lifespan=lifespan,
              docs_url="/docs" if settings.is_dev else None, redoc_url=None,
              openapi_url="/openapi.json" if settings.is_dev else None)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex[:12]
    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    # Log method/path/status only: never bodies, cookies or tokens
    log.info("%s %s -> %s (%d ms) [%s]", request.method, request.url.path, response.status_code,
             (time.monotonic() - start) * 1000, request.state.request_id)
    return response


install_error_handlers(app)
app.include_router(api_router, prefix="/api/v1")
