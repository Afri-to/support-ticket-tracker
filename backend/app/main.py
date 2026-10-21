"""Support Ticket Tracker API: entry point."""

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import auth, kpis
from app.config import get_settings
from app.db import SessionLocal, get_db, init_db
from app.demo import ensure_demo_user
from app.importer import ImportFileError, import_csv
from app.models import Agent, Import, User
from app.schemas import (
    AgentKpiOut,
    AgentOut,
    Credentials,
    ImportOut,
    ImportSummaryOut,
    RootCauseOut,
    SummaryOut,
    TicketPage,
    UserOut,
    WeekOut,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if get_settings().seed_demo:
        with SessionLocal() as db:
            ensure_demo_user(db)
    yield


app = FastAPI(
    title="Support Ticket Tracker API",
    description="Imports support tickets from CSV, cleans them, and serves KPIs. Fake data only.",
    version="0.2.0",
    lifespan=lifespan,
)

DbSession = Annotated[Session, Depends(get_db)]
SessionCookie = Annotated[str | None, Cookie(alias=auth.COOKIE_NAME)]


def current_user(db: DbSession, token: SessionCookie = None) -> User:
    user = auth.user_for_token(db, token)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        token,
        max_age=int(auth.SESSION_LENGTH.total_seconds()),
        httponly=True,  # page scripts can't read it, so an XSS bug can't steal it
        samesite="lax",  # not sent on cross-site form posts (CSRF protection)
        secure=get_settings().secure_cookies,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- Accounts ----------------------------------------------------------------


@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["auth"])
def register(body: Credentials, response: Response, db: DbSession) -> User:
    user = User(email=auth.normalize_email(body.email), password_hash=auth.hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists. Sign in instead.")
    set_session_cookie(response, auth.start_session(db, user))
    return user


@app.post("/auth/login", response_model=UserOut, tags=["auth"])
def login(body: Credentials, response: Response, db: DbSession) -> User:
    user = auth.authenticate(db, body.email, body.password)
    if user is None:
        # Same message for unknown email and wrong password, so it doesn't reveal which emails have accounts.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    set_session_cookie(response, auth.start_session(db, user))
    return user


@app.post("/auth/demo", response_model=UserOut, tags=["auth"])
def demo_login(response: Response, db: DbSession) -> User:
    """Sign in to the shared, read-only demo account."""
    user = ensure_demo_user(db)
    set_session_cookie(response, auth.start_session(db, user))
    return user


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def logout(response: Response, db: DbSession, token: SessionCookie = None) -> None:
    auth.end_session(db, token)
    response.delete_cookie(auth.COOKIE_NAME)


@app.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user: CurrentUser) -> User:
    return user


# --- Imports -------------------------------------------------------------------


@app.post("/imports", response_model=ImportSummaryOut, status_code=status.HTTP_201_CREATED, tags=["imports"])
async def upload_csv(file: UploadFile, db: DbSession, user: CurrentUser):
    """Upload a ticket CSV. Returns how many rows were imported, skipped, or rejected, and why."""
    if user.is_demo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The demo account is read-only. Create a free account to import your own file.")
    limit = get_settings().max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Files up to {limit // (1024 * 1024)} MB.")
    try:
        return import_csv(db, user.id, file.filename or "upload.csv", content)
    except ImportFileError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@app.get("/imports", response_model=list[ImportOut], tags=["imports"])
def list_imports(db: DbSession, user: CurrentUser) -> list[Import]:
    """Your past uploads, newest first."""
    return list(db.scalars(select(Import).where(Import.user_id == user.id).order_by(Import.id.desc())))


# --- KPIs and tickets ----------------------------------------------------------


@app.get("/agents", response_model=list[AgentOut], tags=["kpis"])
def list_agents(db: DbSession, user: CurrentUser) -> list[Agent]:
    """Your agents, A to Z, for the dashboard's agent filter."""
    return list(db.scalars(select(Agent).where(Agent.user_id == user.id).order_by(Agent.name)))


def kpi_filters(
    user: CurrentUser,
    agent_id: Annotated[int | None, Query(description="Only this agent's tickets")] = None,
    date_from: Annotated[date | None, Query(alias="from", description="Opened on or after (YYYY-MM-DD)")] = None,
    date_to: Annotated[date | None, Query(alias="to", description="Opened on or before (YYYY-MM-DD)")] = None,
) -> kpis.Filters:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'from' must be on or before 'to'.")
    return kpis.Filters(user.id, agent_id, date_from, date_to)


KpiFilters = Annotated[kpis.Filters, Depends(kpi_filters)]


@app.get("/kpis/summary", response_model=SummaryOut, tags=["kpis"])
def kpi_summary(db: DbSession, f: KpiFilters):
    """Total and open tickets, plus average and median hours to resolve."""
    return kpis.summary(db, f)


@app.get("/kpis/weekly", response_model=list[WeekOut], tags=["kpis"])
def kpi_weekly(db: DbSession, f: KpiFilters):
    """Tickets opened and closed per week (weeks start Monday), with average hours to resolve."""
    return kpis.weekly(db, f)


@app.get("/kpis/root-causes", response_model=list[RootCauseOut], tags=["kpis"])
def kpi_root_causes(db: DbSession, f: KpiFilters, limit: Annotated[int, Query(ge=1, le=50)] = 5):
    """Most common root causes and their share of all tickets."""
    return kpis.root_causes(db, f, limit)


@app.get("/kpis/agents", response_model=list[AgentKpiOut], tags=["kpis"])
def kpi_agents(db: DbSession, f: KpiFilters):
    """Ticket volume, open tickets and average hours to resolve per agent."""
    return kpis.agents(db, f)


@app.get("/tickets", response_model=TicketPage, tags=["tickets"])
def list_tickets(
    db: DbSession,
    f: KpiFilters,
    search: Annotated[str | None, Query(max_length=100, description="Ticket ID, agent, category or root cause")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Tickets matching the filters, newest first, with the total count for paging."""
    return kpis.tickets(db, f, search, limit, offset)


# --- The dashboard -------------------------------------------------------------
# In production the API also serves the built React app, so both share one
# origin (no CORS, and the session cookie just works). In development Vite
# serves the app instead and this block is skipped.

FRONTEND_DIST = get_settings().frontend_dist
if FRONTEND_DIST and (Path(FRONTEND_DIST) / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=Path(FRONTEND_DIST) / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def dashboard() -> FileResponse:
        return FileResponse(Path(FRONTEND_DIST) / "index.html")
