"""KPI queries, written as plain SQL so each one is easy to read and explain.

Every query is limited to the signed-in user's tickets and shares the same
optional filters, applied to when a ticket was opened: one agent, a start
date, and an end date (inclusive). Values are
always passed as bound parameters, never pasted into the SQL string.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

# CAST(... AS type) IS NULL lets one query serve both "filter" and "no filter":
# when a parameter is NULL its condition is simply true.
FILTERS = """
    t.user_id = :user_id
    AND (CAST(:agent_id AS integer) IS NULL OR t.agent_id = :agent_id)
    AND (CAST(:date_from AS date) IS NULL OR t.opened_at >= CAST(:date_from AS date))
    AND (CAST(:date_to AS date) IS NULL OR t.opened_at < CAST(:date_to AS date) + 1)
"""

# Hours between opening and closing; NULL while a ticket is still open.
RESOLVE_HOURS = "EXTRACT(EPOCH FROM (t.closed_at - t.opened_at)) / 3600"

SUMMARY_SQL = f"""
SELECT
    COUNT(*)                                        AS total,
    COUNT(*) FILTER (WHERE t.closed_at IS NULL)     AS open,
    ROUND(AVG({RESOLVE_HOURS})::numeric, 1)         AS avg_resolve_hours,
    ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {RESOLVE_HOURS}))::numeric, 1)
                                                    AS median_resolve_hours
FROM tickets t
WHERE {FILTERS}
"""

WEEKLY_SQL = f"""
SELECT
    DATE_TRUNC('week', t.opened_at AT TIME ZONE 'UTC')::date AS week_start,  -- Monday
    COUNT(*)                                                 AS opened,
    COUNT(t.closed_at)                                       AS closed,
    ROUND(AVG({RESOLVE_HOURS})::numeric, 1)                  AS avg_resolve_hours
FROM tickets t
WHERE {FILTERS}
GROUP BY week_start
ORDER BY week_start
"""

ROOT_CAUSES_SQL = f"""
SELECT
    c.name                                                  AS category,
    t.root_cause,
    COUNT(*)                                                AS tickets,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)      AS share_pct
FROM tickets t
JOIN categories c ON c.id = t.category_id
WHERE {FILTERS}
GROUP BY c.name, t.root_cause
ORDER BY tickets DESC, category, t.root_cause
LIMIT :limit
"""

AGENTS_SQL = f"""
SELECT
    a.id                                          AS agent_id,
    a.name                                        AS agent,
    COUNT(*)                                      AS tickets,
    COUNT(*) FILTER (WHERE t.closed_at IS NULL)   AS open,
    ROUND(AVG({RESOLVE_HOURS})::numeric, 1)       AS avg_resolve_hours
FROM tickets t
JOIN agents a ON a.id = t.agent_id
WHERE {FILTERS}
GROUP BY a.id, a.name
ORDER BY tickets DESC, a.name
"""


@dataclass(frozen=True)
class Filters:
    user_id: int
    agent_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None

    def params(self) -> dict:
        return {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }


def _rows(db: Session, sql: str, params: dict) -> list[dict]:
    return [dict(row) for row in db.execute(text(sql), params).mappings()]


def summary(db: Session, f: Filters) -> dict:
    return _rows(db, SUMMARY_SQL, f.params())[0]


def weekly(db: Session, f: Filters) -> list[dict]:
    return _rows(db, WEEKLY_SQL, f.params())


def root_causes(db: Session, f: Filters, limit: int = 5) -> list[dict]:
    return _rows(db, ROOT_CAUSES_SQL, {**f.params(), "limit": limit})


def agents(db: Session, f: Filters) -> list[dict]:
    return _rows(db, AGENTS_SQL, f.params())


# Search matches ticket ID, agent, category or root cause, case-insensitively.
TICKETS_WHERE = f"""
FROM tickets t
JOIN agents a ON a.id = t.agent_id
JOIN categories c ON c.id = t.category_id
WHERE {FILTERS}
  AND (CAST(:search AS text) IS NULL
       OR t.ticket_id ILIKE :pattern OR a.name ILIKE :pattern
       OR c.name ILIKE :pattern OR t.root_cause ILIKE :pattern)
"""

TICKETS_SQL = f"""
SELECT t.ticket_id, a.name AS agent, c.name AS category, t.root_cause,
       t.priority::text AS priority, t.opened_at, t.closed_at,
       ROUND(({RESOLVE_HOURS})::numeric, 1) AS resolve_hours
{TICKETS_WHERE}
ORDER BY t.opened_at DESC, t.ticket_id
LIMIT :limit OFFSET :offset
"""

TICKETS_COUNT_SQL = f"SELECT COUNT(*) AS total {TICKETS_WHERE}"


def _like_pattern(search: str) -> str:
    """Escape LIKE wildcards so a search for '50%' matches the text '50%'."""
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def tickets(db: Session, f: Filters, search: str | None, limit: int, offset: int) -> dict:
    search = (search or "").strip() or None
    params = {**f.params(), "search": search, "pattern": _like_pattern(search) if search else None}
    total = _rows(db, TICKETS_COUNT_SQL, params)[0]["total"]
    items = _rows(db, TICKETS_SQL, {**params, "limit": limit, "offset": offset})
    return {"total": total, "items": items}
