"""KPI queries, written as plain SQL so each one is easy to read and explain.

Every query shares the same optional filters, applied to when a ticket was
opened: one agent, a start date, and an end date (inclusive). Values are
always passed as bound parameters, never pasted into the SQL string.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

# CAST(... AS type) IS NULL lets one query serve both "filter" and "no filter":
# when a parameter is NULL its condition is simply true.
FILTERS = """
    (CAST(:agent_id AS integer) IS NULL OR t.agent_id = :agent_id)
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
    agent_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None

    def params(self) -> dict:
        return {"agent_id": self.agent_id, "date_from": self.date_from, "date_to": self.date_to}


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
