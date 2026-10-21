"""The shared, read-only demo account, filled with the sample tickets.

Recruiters can explore the dashboard without signing up. The account can't
import files, so nobody can change what the next visitor sees.
"""

import logging
import secrets
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.importer import import_csv
from app.models import User

DEMO_EMAIL = "demo@support-ticket-tracker.dev"
SAMPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "sample_tickets.csv"
log = logging.getLogger(__name__)


def ensure_demo_user(db: Session, sample: Path = SAMPLE_CSV) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is not None:
        return user
    # Nobody signs in with this password; the "Explore the demo" button
    # starts a demo session directly.
    user = User(email=DEMO_EMAIL, password_hash=hash_password(secrets.token_urlsafe(24)), is_demo=True)
    db.add(user)
    db.commit()
    if sample.exists():
        summary = import_csv(db, user.id, sample.name, sample.read_bytes())
        log.info("Demo account seeded with %s tickets", summary.imported)
    else:
        log.warning("Sample CSV not found at %s; demo account is empty", sample)
    return user
