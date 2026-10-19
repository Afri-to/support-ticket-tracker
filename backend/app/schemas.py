"""Response models for the API."""

from datetime import datetime

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
