from datetime import timezone

import pytest

from app.models import Priority
from app.validation import RowError, clean_text, parse_datetime, validate_row
from tests.conftest import ticket


def codes(result):
    return [p.code for p in result.problems]


def test_valid_row_becomes_a_clean_ticket():
    result = validate_row(ticket())
    assert result.problems == []
    assert result.ticket.priority is Priority.HIGH
    assert result.ticket.opened_at.tzinfo is timezone.utc


def test_whitespace_is_tidied():
    result = validate_row(ticket(agent="  Ana    Torres ", category=" Network"))
    assert result.ticket.agent == "Ana Torres"
    assert result.ticket.category == "Network"


@pytest.mark.parametrize("value", ["high", "HIGH", " High "])
def test_priority_ignores_case_and_spaces(value):
    assert validate_row(ticket(priority=value)).ticket.priority is Priority.HIGH


def test_open_ticket_has_no_closed_at():
    assert validate_row(ticket(closed_at="")).ticket.closed_at is None


@pytest.mark.parametrize("field", ["ticket_id", "agent", "category", "root_cause", "priority", "opened_at"])
def test_required_fields(field):
    assert RowError.MISSING_FIELD in codes(validate_row(ticket(**{field: "  "})))


@pytest.mark.parametrize("value", ["TKT000001", "TCK-1", "tck-000001", "TCK-0000001"])
def test_ticket_id_format(value):
    assert codes(validate_row(ticket(ticket_id=value))) == [RowError.INVALID_TICKET_ID]


@pytest.mark.parametrize("value", ["Urgent", "P1", "???"])
def test_unknown_priority(value):
    assert codes(validate_row(ticket(priority=value))) == [RowError.UNKNOWN_PRIORITY]


@pytest.mark.parametrize("value", ["31/02/2026", "yesterday", "2026-02-30T10:00"])
def test_bad_dates(value):
    assert codes(validate_row(ticket(opened_at=value))) == [RowError.INVALID_DATE]
    assert codes(validate_row(ticket(closed_at=value))) == [RowError.INVALID_DATE]


def test_closed_before_opened():
    result = validate_row(ticket(opened_at="2026-07-06T09:00", closed_at="2026-07-06T08:59"))
    assert codes(result) == [RowError.CLOSED_BEFORE_OPENED]


def test_several_problems_are_all_reported():
    result = validate_row(ticket(agent="", priority="P1", opened_at="nope"))
    assert set(codes(result)) == {RowError.MISSING_FIELD, RowError.UNKNOWN_PRIORITY, RowError.INVALID_DATE}


def test_explicit_timezone_is_kept():
    assert parse_datetime("2026-07-06T09:00-04:00").utcoffset().total_seconds() == -4 * 3600


def test_clean_text_handles_none():
    assert clean_text(None) == ""
