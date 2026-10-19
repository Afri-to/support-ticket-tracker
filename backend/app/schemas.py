"""Response models for the API."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.validation import RowError


class ProblemOut(BaseModel):
    code: RowError
    message: str


class RowReportOut(BaseModel):
    line: int
    ticket_id: str
    problems: list[ProblemOut]


class ImportSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    import_id: int
    filename: str
    total_rows: int
    imported: int
    duplicates: int
    already_imported: int
    invalid: int
    errors: list[RowReportOut]


class ImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    created_at: datetime
    total_rows: int
    imported: int
    duplicates: int
    already_imported: int
    invalid: int


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class SummaryOut(BaseModel):
    total: int
    open: int
    avg_resolve_hours: Decimal | None
    median_resolve_hours: Decimal | None


class WeekOut(BaseModel):
    week_start: date
    opened: int
    closed: int
    avg_resolve_hours: Decimal | None


class RootCauseOut(BaseModel):
    category: str
    root_cause: str
    tickets: int
    share_pct: Decimal


class AgentKpiOut(BaseModel):
    agent_id: int
    agent: str
    tickets: int
    open: int
    avg_resolve_hours: Decimal | None
