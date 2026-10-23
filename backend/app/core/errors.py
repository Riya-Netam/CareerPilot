import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import ErrorEvent

log = logging.getLogger("careerpilot")


def _body(code: str, message: str, details=None, request_id: str | None = None) -> dict:
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    if request_id:
        err["request_id"] = request_id
    return {"error": err}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request: Request, exc: StarletteHTTPException):
        d = exc.detail
        if isinstance(d, dict) and "code" in d:
            body = _body(d["code"], d.get("message", ""))
        else:
            body = _body("http_error", str(d))
        return JSONResponse(body, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_exc(request: Request, exc: RequestValidationError):
        details = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse(_body("validation_error", "Some fields are invalid.", details), status_code=422)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", uuid.uuid4().hex[:12])
        log.error("Unhandled %s on %s %s [request_id=%s]", type(exc).__name__, request.method, request.url.path, rid)
        try:
            with SessionLocal() as db:
                db.add(ErrorEvent(request_id=rid, method=request.method, path=request.url.path[:300], error_type=type(exc).__name__))
                db.commit()
        except Exception:
            pass
        msg = "Something went wrong on our side." if not get_settings().is_dev else f"{type(exc).__name__}: {exc}"
        return JSONResponse(_body("internal_error", msg, request_id=rid), status_code=500)
