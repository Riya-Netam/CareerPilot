import pytest
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models import JobApplication, User
from app.tests.conftest import make_user


def test_unique_email_enforced(db):
    make_user(db, "dup@example.com")
    db.add(User(email="dup@example.com", password_hash=hash_password("x1234567890a"), full_name="x"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_invalid_role_rejected_by_database(db):
    db.add(User(email="r@example.com", password_hash="x", full_name="x", role="GOD"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_invalid_application_status_rejected_by_database(db):
    u = make_user(db)
    db.add(JobApplication(user_id=u.id, company="A", job_title="B", status="HIRED"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_deleting_user_cascades(db):
    u = make_user(db)
    db.add(JobApplication(user_id=u.id, company="A", job_title="B"))
    db.commit()
    db.delete(u); db.commit()
    assert db.query(JobApplication).count() == 0
