from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import (SESSION_COOKIE, api_error, clear_session_cookies, get_current_user, start_session)
from app.core.ratelimit import rate_limit
from app.core.security import (as_utc, hash_password, hash_token, needs_rehash, new_token, utcnow, verify_password)
from app.db.session import get_db
from app.models import EmailVerificationToken, PasswordResetToken, User, UserSession
from app.schemas.auth import (ChangePasswordIn, EmailIn, LoginIn, RegisterIn, ResetPasswordIn, TokenIn, UserOut)
from app.schemas.common import Message
from app.services.audit import audit
from app.services.email import send_email

router = APIRouter(prefix="/auth", tags=["auth"])
GENERIC = "If that email can be used, we have sent instructions to it."


def _issue_verification(db: Session, user: User, tasks: BackgroundTasks) -> None:
    raw = new_token()
    db.add(EmailVerificationToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() + timedelta(hours=24)))
    db.commit()
    link = f"{get_settings().FRONTEND_URL.rstrip('/')}/verify-email?token={raw}"
    tasks.add_task(send_email, user.email, "Verify your CareerPilot AI email",
                   f"Hi {user.full_name},\n\nConfirm your email to activate your account (link valid for 24 hours):\n{link}\n\nIf you did not sign up, ignore this email.",
                   dev_link=link)


@router.post("/register", status_code=202, response_model=Message, dependencies=[Depends(rate_limit("register", 5, 3600))])
def register(body: RegisterIn, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = body.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is None:
        user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name, role="USER")
        db.add(user); db.commit()
        _issue_verification(db, user, tasks)
    elif existing.email_verified_at is None and existing.is_active:
        _issue_verification(db, existing, tasks)  # resend; never reveals that the account exists
    # Same response whether or not the email was already registered
    return Message(message="Check your email to verify your account.")


@router.post("/verify-email", response_model=Message, dependencies=[Depends(rate_limit("verify", 20, 3600))])
def verify_email(body: TokenIn, db: Session = Depends(get_db)):
    tok = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == hash_token(body.token)))
    if not tok or tok.used_at is not None or as_utc(tok.expires_at) <= utcnow():
        raise api_error(400, "invalid_token", "This verification link is invalid or has expired.")
    user = db.get(User, tok.user_id)
    tok.used_at = utcnow()
    if user and user.email_verified_at is None:
        user.email_verified_at = utcnow()
    db.commit()
    return Message(message="Email verified. You can sign in now.")


@router.post("/resend-verification", response_model=Message, dependencies=[Depends(rate_limit("resend", 5, 3600))])
def resend_verification(body: EmailIn, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active and user.email_verified_at is None:
        _issue_verification(db, user, tasks)
    return Message(message=GENERIC)


@router.post("/login", response_model=UserOut, dependencies=[Depends(rate_limit("login", 10, 900))])
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        raise api_error(401, "invalid_credentials", "Email or password is incorrect.")
    if not user.is_active:
        raise api_error(403, "account_disabled", "This account is disabled.")
    if user.email_verified_at is None:
        raise api_error(403, "email_not_verified", "Please verify your email before signing in.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    user.last_login_at = utcnow()
    start_session(db, user, request, response)
    db.commit()
    return user


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    request.state.session.revoked_at = utcnow()
    db.commit()
    clear_session_cookies(response)
    return Message(message="Signed out.")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/forgot-password", response_model=Message, dependencies=[Depends(rate_limit("forgot", 5, 3600))])
def forgot_password(body: EmailIn, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        raw = new_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() + timedelta(hours=1)))
        db.commit()
        link = f"{get_settings().FRONTEND_URL.rstrip('/')}/reset-password?token={raw}"
        tasks.add_task(send_email, user.email, "Reset your CareerPilot AI password",
                       f"Use this link within 1 hour to choose a new password:\n{link}\n\nIf you did not ask for this, ignore this email.", dev_link=link)
    return Message(message=GENERIC)


@router.post("/reset-password", response_model=Message, dependencies=[Depends(rate_limit("reset", 10, 3600))])
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)):
    tok = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(body.token)))
    if not tok or tok.used_at is not None or as_utc(tok.expires_at) <= utcnow():
        raise api_error(400, "invalid_token", "This reset link is invalid or has expired.")
    user = db.get(User, tok.user_id)
    if not user:
        raise api_error(400, "invalid_token", "This reset link is invalid or has expired.")
    user.password_hash = hash_password(body.password)
    tok.used_at = utcnow()
    # Receiving the email proves ownership of it; also sign out everywhere
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    db.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.commit()
    return Message(message="Password updated. Please sign in.")


@router.post("/change-password", response_model=Message, dependencies=[Depends(rate_limit("change_pw", 10, 3600))])
def change_password(body: ChangePasswordIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise api_error(400, "wrong_password", "Your current password is incorrect.")
    user.password_hash = hash_password(body.new_password)
    current = request.state.session
    db.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None),
                                         UserSession.id != current.id).values(revoked_at=utcnow()))
    db.commit()
    return Message(message="Password changed. Other devices were signed out.")
