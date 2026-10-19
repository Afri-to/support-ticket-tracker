"""Support Ticket Tracker API: entry point."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db, init_db
from app.importer import ImportFileError, import_csv
from app.models import Import
from app.schemas import ImportOut, ImportSummaryOut


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
