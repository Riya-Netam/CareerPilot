from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import as_utc, hash_token, new_token, safe_equal, utcnow
from app.db.session import get_db
from app.models import User, UserSession

SESSION_COOKIE = "cp_session"
CSRF_COOKIE = "cp_csrf"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def api_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, detail={"code": code, "message": message})


def start_session(db: Session, user: User, request: Request, response: Response) -> None:
    s = get_settings()
    raw = new_token()
    exp = utcnow() + timedelta(days=s.SESSION_DAYS)
    db.add(UserSession(user_id=user.id, token_hash=hash_token(raw), created_at=utcnow(), expires_at=exp,
                       user_agent=(request.headers.get("user-agent") or "")[:300]))
    csrf = new_token()
    common = dict(max_age=s.SESSION_DAYS * 86400, secure=s.COOKIE_SECURE, samesite=s.COOKIE_SAMESITE, path="/")
    response.set_cookie(SESSION_COOKIE, raw, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, csrf, httponly=False, **common)  # readable by our own JS (double-submit)


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def _load_session(request: Request, db: Session) -> UserSession:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        raise api_error(401, "not_authenticated", "Please sign in.")
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(raw)))
    if not sess or sess.revoked_at is not None or as_utc(sess.expires_at) <= utcnow():
        raise api_error(401, "session_expired", "Your session has expired. Please sign in again.")
    return sess


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    sess = _load_session(request, db)
    if request.method not in SAFE_METHODS:  # CSRF double-submit check for state-changing requests
        cookie, header = request.cookies.get(CSRF_COOKIE, ""), request.headers.get(CSRF_HEADER, "")
        if not cookie or not header or not safe_equal(cookie, header):
            raise api_error(403, "csrf_failed", "Security check failed. Refresh the page and try again.")
    user = db.get(User, sess.user_id)
    if not user or not user.is_active:
        raise api_error(403, "account_disabled", "This account is disabled.")
    request.state.session = sess
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("ADMIN", "SUPER_ADMIN"):
        raise api_error(403, "forbidden", "You do not have access to this area.")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "SUPER_ADMIN":
        raise api_error(403, "forbidden", "You do not have access to this area.")
    return user


def owned_or_404(obj, user: User):
    """Ownership check that does not reveal whether someone else's object exists."""
    if obj is None or obj.user_id != user.id:
        raise api_error(404, "not_found", "Not found.")
    return obj
