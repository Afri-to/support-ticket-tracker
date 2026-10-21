"""Accounts, password hashing and sessions.

Passwords are hashed with scrypt (Python's standard library), each with its
own random salt. A session is a random token in an HttpOnly cookie; the
database keeps only its SHA-256 hash, so a leaked database can't be used to
sign in as anyone.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import SessionToken, User

COOKIE_NAME = "stt_session"
SESSION_LENGTH = timedelta(days=7)
SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)  # constant-time comparison


# A real hash to check against when the email doesn't exist, so a wrong email
# takes as long as a wrong password and response times don't reveal accounts.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user.password_hash) else None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SessionToken(token_hash=_token_hash(token), user_id=user.id, expires_at=datetime.now(timezone.utc) + SESSION_LENGTH))
    db.commit()
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.get(SessionToken, _token_hash(token))
    if session is None or session.expires_at <= datetime.now(timezone.utc):
        return None
    return session.user


def end_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(SessionToken).where(SessionToken.token_hash == _token_hash(token)))
        db.commit()
