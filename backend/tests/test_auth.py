import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import auth
from app.db import SessionLocal
from app.demo import DEMO_EMAIL, ensure_demo_user
from app.main import app
from app.models import SessionToken, User
from tests.conftest import PASSWORD, ticket, upload


def creds(email="ana@example.com", password=PASSWORD):
    return {"email": email, "password": password}


# --- passwords ---------------------------------------------------------------


def test_password_hash_round_trip():
    stored = auth.hash_password("s3cret-password")
    assert stored.startswith("scrypt$") and "s3cret" not in stored
    assert auth.verify_password("s3cret-password", stored)
    assert not auth.verify_password("wrong-password", stored)


def test_same_password_gets_different_salts():
    assert auth.hash_password("same-password") != auth.hash_password("same-password")


@pytest.mark.parametrize("stored", ["", "md5$abc$def", "scrypt$nothex"])
def test_malformed_hashes_never_verify(stored):
    assert not auth.verify_password("anything", stored)


# --- register / login / logout ---------------------------------------------------


def test_register_signs_you_in(anon):
    response = anon.post("/auth/register", json=creds())
    assert response.status_code == 201
    assert response.json() == {"email": "ana@example.com", "is_demo": False}
    assert anon.get("/auth/me").json()["email"] == "ana@example.com"


def test_session_cookie_is_httponly(anon):
    cookie = anon.post("/auth/register", json=creds()).headers["set-cookie"]
    assert "HttpOnly" in cookie and "samesite=lax" in cookie.lower()


def test_email_is_case_insensitive(anon):
    anon.post("/auth/register", json=creds("Ana@Example.COM"))
    anon.post("/auth/logout")
    assert anon.post("/auth/login", json=creds("ana@example.com")).status_code == 200


def test_duplicate_email_is_rejected(anon):
    anon.post("/auth/register", json=creds())
    response = anon.post("/auth/register", json=creds())
    assert response.status_code == 409


@pytest.mark.parametrize("body", [
    {"email": "not-an-email", "password": PASSWORD},
    {"email": "ana@example.com", "password": "short"},
    {"email": "ana@example.com"},
])
def test_register_validation(anon, body):
    assert anon.post("/auth/register", json=body).status_code == 422


def test_login_and_logout(anon):
    anon.post("/auth/register", json=creds())
    anon.post("/auth/logout")
    assert anon.get("/auth/me").status_code == 401
    assert anon.post("/auth/login", json=creds()).status_code == 200
    assert anon.get("/auth/me").status_code == 200


def test_wrong_password_and_unknown_email_get_the_same_answer(anon):
    anon.post("/auth/register", json=creds())
    anon.post("/auth/logout")
    wrong = anon.post("/auth/login", json=creds(password="wrong password"))
    unknown = anon.post("/auth/login", json=creds("nobody@example.com"))
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_logout_deletes_the_session(anon):
    anon.post("/auth/register", json=creds())
    anon.post("/auth/logout")
    with SessionLocal() as db:
        assert db.scalars(select(SessionToken)).all() == []


def test_only_a_hash_of_the_token_is_stored(anon):
    token = anon.post("/auth/register", json=creds()).cookies[auth.COOKIE_NAME]
    with SessionLocal() as db:
        stored = db.scalars(select(SessionToken.token_hash)).one()
    assert token not in stored and len(stored) == 64


def test_expired_session_is_refused(anon):
    from datetime import datetime, timedelta, timezone

    anon.post("/auth/register", json=creds())
    with SessionLocal() as db:
        session = db.scalars(select(SessionToken)).one()
        session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert anon.get("/auth/me").status_code == 401


@pytest.mark.parametrize("path", ["/agents", "/imports", "/kpis/summary", "/kpis/weekly", "/kpis/root-causes", "/kpis/agents", "/tickets"])
def test_data_needs_sign_in(anon, path):
    response = anon.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Sign in to continue."


def test_upload_needs_sign_in(anon):
    assert upload(anon, [ticket()]).status_code == 401


def test_forged_cookie_is_refused(anon):
    anon.cookies.set(auth.COOKIE_NAME, "made-up-token")
    assert anon.get("/auth/me").status_code == 401


# --- each user sees only their own data ------------------------------------------


def test_users_cannot_see_each_others_tickets(anon):
    with TestClient(app) as ben:
        anon.post("/auth/register", json=creds("ana@example.com"))
        ben.post("/auth/register", json=creds("ben@example.com"))

        upload(anon, [ticket(ticket_id="TCK-000001", agent="Ana's agent")])
        upload(ben, [ticket(ticket_id="TCK-000001", agent="Ben's agent"), ticket(ticket_id="TCK-000002", agent="Ben's agent")])

        assert anon.get("/kpis/summary").json()["total"] == 1
        assert ben.get("/kpis/summary").json()["total"] == 2
        assert [a["name"] for a in anon.get("/agents").json()] == ["Ana's agent"]
        assert [t["agent"] for t in anon.get("/tickets").json()["items"]] == ["Ana's agent"]
        assert len(anon.get("/imports").json()) == 1


def test_same_ticket_id_can_exist_for_two_users(anon):
    with TestClient(app) as ben:
        anon.post("/auth/register", json=creds("ana@example.com"))
        ben.post("/auth/register", json=creds("ben@example.com"))
        assert upload(anon, [ticket()]).json()["imported"] == 1
        assert upload(ben, [ticket()]).json()["imported"] == 1  # not "already imported"


def test_filtering_by_another_users_agent_returns_nothing(anon):
    with TestClient(app) as ben:
        anon.post("/auth/register", json=creds("ana@example.com"))
        ben.post("/auth/register", json=creds("ben@example.com"))
        upload(ben, [ticket()])
        bens_agent = ben.get("/agents").json()[0]["id"]
        upload(anon, [ticket()])
        assert anon.get("/kpis/summary", params={"agent_id": bens_agent}).json()["total"] == 0


# --- demo account -------------------------------------------------------------------


def test_demo_account_is_seeded_once(anon, tmp_path):
    sample = tmp_path / "sample.csv"
    from tests.conftest import to_csv

    sample.write_bytes(to_csv([ticket(), ticket(ticket_id="TCK-000002")]))
    with SessionLocal() as db:
        first = ensure_demo_user(db, sample)
        second = ensure_demo_user(db, sample)
        assert first.id == second.id and first.is_demo
        assert db.scalars(select(User).where(User.email == DEMO_EMAIL)).one()


def test_demo_button_signs_in_to_sample_data(anon):
    response = anon.post("/auth/demo")
    assert response.json() == {"email": DEMO_EMAIL, "is_demo": True}
    assert anon.get("/kpis/summary").json()["total"] == 4789  # the full sample file


def test_demo_account_is_read_only(anon):
    anon.post("/auth/demo")
    response = upload(anon, [ticket(ticket_id="TCK-999999")])
    assert response.status_code == 403
    assert "read-only" in response.json()["detail"]


def test_demo_password_cannot_be_guessed_from_code(anon):
    anon.post("/auth/demo")
    anon.post("/auth/logout")
    assert anon.post("/auth/login", json={"email": DEMO_EMAIL, "password": "demo-password"}).status_code == 401
