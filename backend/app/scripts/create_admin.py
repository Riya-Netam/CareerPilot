"""Create or promote the first administrator safely.

Usage (from the backend folder, with the venv active and the database migrated):
    python -m app.scripts.create_admin --email you@example.com --role SUPER_ADMIN

The password is typed at a hidden prompt (or read from ADMIN_PASSWORD) and is never stored in
a file. This is the ONLY way to create ADMIN/SUPER_ADMIN accounts; the API has no such route.
"""
import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.security import hash_password, password_is_acceptable, utcnow, PASSWORD_RULE
from app.db.session import SessionLocal
from app.models import User
from app.services.audit import audit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", default="Administrator")
    ap.add_argument("--role", choices=["ADMIN", "SUPER_ADMIN"], default="SUPER_ADMIN")
    args = ap.parse_args()
    email = args.email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role, user.is_active = args.role, True
            user.email_verified_at = user.email_verified_at or utcnow()
            print(f"Existing account {email} promoted to {args.role}.")
        else:
            pw = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password for the new admin: ")
            if not password_is_acceptable(pw):
                print(PASSWORD_RULE); return 1
            if not os.environ.get("ADMIN_PASSWORD") and pw != getpass.getpass("Repeat password: "):
                print("Passwords do not match."); return 1
            db.add(User(email=email, password_hash=hash_password(pw), full_name=args.name, role=args.role,
                        email_verified_at=utcnow()))
            print(f"Created {args.role} account {email}.")
        db.flush()
        audit(db, None, "admin.bootstrap", "user", email, {"role": args.role, "via": "cli"})
        db.commit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
