"""Read an uploaded CSV, keep the good rows, and explain the rest.

Order of checks for each row:
  1. Validate it (missing fields, bad dates, unknown priority, ...).
  2. Drop it if it's an exact copy of an earlier row in the same file.
  3. Reject it if it reuses an earlier row's ticket_id with different values.
  4. Skip it if that ticket_id was already imported from an earlier file.
"""

import csv
import io
from dataclasses import dataclass, field

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.models import Agent, Category, Import, Ticket
from app.validation import REQUIRED_COLUMNS, CleanTicket, Problem, RowError, validate_row

MAX_REPORTED_ERRORS = 100


class ImportFileError(ValueError):
    """The file as a whole can't be read (wrong encoding, missing columns...)."""


@dataclass
class RowReport:
    line: int  # line number in the file, counting the header as line 1
    ticket_id: str
    problems: list[Problem]


@dataclass
class ImportSummary:
    import_id: int
    filename: str
    total_rows: int = 0
    imported: int = 0
    duplicates: int = 0
    already_imported: int = 0
    invalid: int = 0
    errors: list[RowReport] = field(default_factory=list)


def read_rows(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")  # -sig drops the BOM Excel adds
    except UnicodeDecodeError as exc:
        raise ImportFileError("The file isn't UTF-8 text. Export it as CSV (UTF-8) and try again.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ImportFileError("The file is empty.")
    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ImportFileError(f"Missing columns: {', '.join(missing)}.")
    reader.fieldnames = headers
    return list(reader)


def _get_or_create(db: Session, model, names: set[str]) -> dict[str, int]:
    """Map each name to its id, inserting any names not seen before."""
    existing = dict(db.execute(select(model.name, model.id).where(model.name.in_(names))).all())
    new = names - existing.keys()
    if new:
        db.execute(insert(model), [{"name": n} for n in sorted(new)])
        existing = dict(db.execute(select(model.name, model.id).where(model.name.in_(names))).all())
    return existing


def import_csv(db: Session, filename: str, content: bytes) -> ImportSummary:
    rows = read_rows(content)
    batch = Import(filename=filename, total_rows=len(rows), imported=0, duplicates=0, already_imported=0, invalid=0)
    db.add(batch)
    db.flush()  # assigns batch.id

    summary = ImportSummary(import_id=batch.id, filename=filename, total_rows=len(rows))
    seen: dict[str, tuple[int, CleanTicket]] = {}
    keep: list[CleanTicket] = []

    def reject(line: int, ticket_id: str, problems: list[Problem]) -> None:
        summary.invalid += 1
        if len(summary.errors) < MAX_REPORTED_ERRORS:
            summary.errors.append(RowReport(line, ticket_id, problems))

    for index, raw in enumerate(rows):
        line = index + 2  # +1 for the header, +1 because lines start at 1
        result = validate_row(raw)
        if result.ticket is None:
            reject(line, (raw.get("ticket_id") or "").strip(), result.problems)
            continue
        ticket = result.ticket
        if ticket.ticket_id in seen:
            first_line, first = seen[ticket.ticket_id]
            if first == ticket:
                summary.duplicates += 1
            else:
                reject(line, ticket.ticket_id, [Problem(
                    RowError.CONFLICTING_DUPLICATE,
                    f"Same ticket_id as line {first_line} but with different values; kept line {first_line}.",
                )])
            continue
        seen[ticket.ticket_id] = (line, ticket)
        keep.append(ticket)

    if keep:
        already = set(db.scalars(select(Ticket.ticket_id).where(Ticket.ticket_id.in_([t.ticket_id for t in keep]))))
        summary.already_imported = len(already)
        keep = [t for t in keep if t.ticket_id not in already]

    if keep:
        agents = _get_or_create(db, Agent, {t.agent for t in keep})
        categories = _get_or_create(db, Category, {t.category for t in keep})
        db.execute(insert(Ticket), [
            {
                "ticket_id": t.ticket_id,
                "agent_id": agents[t.agent],
                "category_id": categories[t.category],
                "root_cause": t.root_cause,
                "priority": t.priority,
                "opened_at": t.opened_at,
                "closed_at": t.closed_at,
                "import_id": batch.id,
            }
            for t in keep
        ])
    summary.imported = len(keep)

    batch.imported = summary.imported
    batch.duplicates = summary.duplicates
    batch.already_imported = summary.already_imported
    batch.invalid = summary.invalid
    db.commit()
    return summary
