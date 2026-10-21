"""Shared test setup: a real PostgreSQL test database, emptied after each test."""

import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/tickets_test"
)
os.environ["SECURE_COOKIES"] = "false"  # the test client talks plain http
os.environ["SEED_DEMO"] = "false"  # demo tests seed it themselves

import csv  # noqa: E402
import io  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.validation import REQUIRED_COLUMNS  # noqa: E402


@pytest.fixture(scope="session")
def _schema():
    init_db()
    yield


PASSWORD = "correct horse battery"


def _truncate():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, sessions, tickets, imports, agents, categories RESTART IDENTITY CASCADE"))


@pytest.fixture
def anon(_schema):
    """A browser that isn't signed in."""
    with TestClient(app) as test_client:
        yield test_client
    _truncate()


@pytest.fixture
def client(anon):
    """A browser signed in as a fresh account."""
    response = anon.post("/auth/register", json={"email": "tester@example.com", "password": PASSWORD})
    assert response.status_code == 201
    return anon


def ticket(**overrides) -> dict:
    row = {
        "ticket_id": "TCK-000001",
        "agent": "Ana Torres",
        "category": "Network",
        "root_cause": "Wi-Fi dropout",
        "priority": "High",
        "opened_at": "2026-07-06T09:00",
        "closed_at": "2026-07-06T13:30",
    }
    row.update(overrides)
    return row


def to_csv(rows: list[dict], columns=REQUIRED_COLUMNS) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def upload(client, rows=None, content=None, filename="tickets.csv"):
    body = content if content is not None else to_csv(rows)
    return client.post("/imports", files={"file": (filename, body, "text/csv")})
