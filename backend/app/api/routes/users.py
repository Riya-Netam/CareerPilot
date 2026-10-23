from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.deps import api_error, clear_session_cookies, get_current_user
from app.core.ratelimit import rate_limit
from app.core.security import verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import DeleteAccountIn, ProfileUpdate, UserOut
from app.schemas.common import Message
from app.services.storage import get_storage

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.full_name = body.full_name.strip()
    db.commit()
    return user


@router.delete("/me", response_model=Message, dependencies=[Depends(rate_limit("delete_account", 5, 3600))])
def delete_account(body: DeleteAccountIn, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes the account and all owned data (database rows cascade) plus stored files."""
    if not verify_password(body.password, user.password_hash):
        raise api_error(400, "wrong_password", "Your password is incorrect.")
    if user.role in ("ADMIN", "SUPER_ADMIN"):
        raise api_error(400, "admin_delete_blocked", "Administrator accounts must be demoted before deletion.")
    get_storage().delete_all(user.id)
    db.delete(user)
    db.commit()
    clear_session_cookies(response)
    return Message(message="Your account and data were deleted.")
