"""Support Ticket Tracker API: entry point."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, init_db
from app.importer import ImportFileError, import_csv
from app import kpis
from app.models import Agent, Import
from app.schemas import (
    AgentKpiOut,
    AgentOut,
    ImportOut,
    ImportSummaryOut,
    RootCauseOut,
    SummaryOut,
    WeekOut,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Support Ticket Tracker API",
    description="Imports support tickets from CSV, cleans them, and serves KPIs. Fake data only.",
    version="0.1.0",
    lifespan=lifespan,
)

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/imports", response_model=ImportSummaryOut, status_code=status.HTTP_201_CREATED, tags=["imports"])
async def upload_csv(file: UploadFile, db: DbSession):
    """Upload a ticket CSV. Returns how many rows were imported, skipped, or rejected, and why."""
    limit = get_settings().max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Files up to {limit // (1024 * 1024)} MB.")
    try:
        return import_csv(db, file.filename or "upload.csv", content)
    except ImportFileError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@app.get("/imports", response_model=list[ImportOut], tags=["imports"])
def list_imports(db: DbSession) -> list[Import]:
    """Past uploads, newest first."""
    return list(db.scalars(select(Import).order_by(Import.id.desc())))


@app.get("/agents", response_model=list[AgentOut], tags=["kpis"])
def list_agents(db: DbSession) -> list[Agent]:
    """Agents for the dashboard's agent filter, A to Z."""
    return list(db.scalars(select(Agent).order_by(Agent.name)))


def kpi_filters(
    agent_id: Annotated[int | None, Query(description="Only this agent's tickets")] = None,
    date_from: Annotated[date | None, Query(alias="from", description="Opened on or after (YYYY-MM-DD)")] = None,
    date_to: Annotated[date | None, Query(alias="to", description="Opened on or before (YYYY-MM-DD)")] = None,
) -> kpis.Filters:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'from' must be on or before 'to'.")
    return kpis.Filters(agent_id, date_from, date_to)


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
