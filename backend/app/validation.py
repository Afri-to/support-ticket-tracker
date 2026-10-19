"""Check one CSV row and turn it into clean values, or explain what's wrong.

Pure functions with no database access, so every rule is unit-tested alone.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.models import Priority

REQUIRED_COLUMNS = ["ticket_id", "agent", "category", "root_cause", "priority", "opened_at", "closed_at"]
TICKET_ID = re.compile(r"TCK-\d{6}")


class RowError(str, Enum):
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_TICKET_ID = "INVALID_TICKET_ID"
    UNKNOWN_PRIORITY = "UNKNOWN_PRIORITY"
    INVALID_DATE = "INVALID_DATE"
    CLOSED_BEFORE_OPENED = "CLOSED_BEFORE_OPENED"
    CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"


@dataclass
class Problem:
    code: RowError
    message: str


@dataclass
class CleanTicket:
    ticket_id: str
    agent: str
    category: str
    root_cause: str
    priority: Priority
    opened_at: datetime
    closed_at: datetime | None


@dataclass
class RowResult:
    ticket: CleanTicket | None = None
    problems: list[Problem] = field(default_factory=list)


def clean_text(value: str | None) -> str:
    """Trim and collapse inner whitespace: '  Jane   Doe ' -> 'Jane Doe'."""
    return " ".join((value or "").split())


def parse_datetime(value: str) -> datetime | None:
    """ISO 8601 only. A time without a zone is treated as UTC."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def validate_row(raw: dict[str, str | None]) -> RowResult:
    row = {key: clean_text(raw.get(key)) for key in REQUIRED_COLUMNS}
    problems: list[Problem] = []

    for name in ("ticket_id", "agent", "category", "root_cause", "priority", "opened_at"):
        if not row[name]:
            problems.append(Problem(RowError.MISSING_FIELD, f"'{name}' is empty."))

    if row["ticket_id"] and not TICKET_ID.fullmatch(row["ticket_id"]):
        problems.append(
            Problem(RowError.INVALID_TICKET_ID, f"'{row['ticket_id']}' should look like TCK-000123.")
        )

    priority = None
    if row["priority"]:
        priority = next((p for p in Priority if p.value.lower() == row["priority"].lower()), None)
        if priority is None:
            allowed = ", ".join(p.value for p in Priority)
            problems.append(
                Problem(RowError.UNKNOWN_PRIORITY, f"'{row['priority']}' isn't one of {allowed}.")
            )

    opened = closed = None
    if row["opened_at"]:
        opened = parse_datetime(row["opened_at"])
        if opened is None:
            problems.append(Problem(RowError.INVALID_DATE, f"opened_at '{row['opened_at']}' isn't a valid date."))
    if row["closed_at"]:
        closed = parse_datetime(row["closed_at"])
        if closed is None:
            problems.append(Problem(RowError.INVALID_DATE, f"closed_at '{row['closed_at']}' isn't a valid date."))
    if opened and closed and closed < opened:
        problems.append(Problem(RowError.CLOSED_BEFORE_OPENED, "closed_at is earlier than opened_at."))

    if problems:
        return RowResult(problems=problems)
    return RowResult(
        ticket=CleanTicket(
            ticket_id=row["ticket_id"],
            agent=row["agent"],
            category=row["category"],
            root_cause=row["root_cause"],
            priority=priority,
            opened_at=opened,
            closed_at=closed,
        )
    )
