"""Integration tests: upload real CSV files to the API backed by PostgreSQL."""

from pathlib import Path

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import Agent, Ticket
from tests.conftest import ticket, to_csv, upload

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "sample_tickets.csv"


def test_clean_file_imports_every_row(client):
    rows = [ticket(ticket_id=f"TCK-{n:06d}") for n in range(1, 6)]
    body = upload(client, rows).json()
    assert body["total_rows"] == 5
    assert body["imported"] == 5
    assert body["duplicates"] == body["invalid"] == body["already_imported"] == 0
    assert body["errors"] == []


def test_exact_duplicates_are_dropped_quietly(client):
    body = upload(client, [ticket(), ticket(), ticket()]).json()
    assert body["imported"] == 1
    assert body["duplicates"] == 2
    assert body["invalid"] == 0


def test_same_id_with_different_values_is_rejected_with_reason(client):
    body = upload(client, [ticket(), ticket(priority="Low")]).json()
    assert body["imported"] == 1
    assert body["invalid"] == 1
    error = body["errors"][0]
    assert error["line"] == 3
    assert error["problems"][0]["code"] == "CONFLICTING_DUPLICATE"
    assert "line 2" in error["problems"][0]["message"]


def test_invalid_rows_report_line_and_reasons(client):
    rows = [ticket(), ticket(ticket_id="TCK-000002", priority="Urgent"), ticket(ticket_id="TCK-000003", agent="")]
    body = upload(client, rows).json()
    assert body["imported"] == 1
    assert body["invalid"] == 2
    assert [(e["line"], e["problems"][0]["code"]) for e in body["errors"]] == [
        (3, "UNKNOWN_PRIORITY"),
        (4, "MISSING_FIELD"),
    ]


def test_second_upload_skips_tickets_already_imported(client):
    upload(client, [ticket(), ticket(ticket_id="TCK-000002")])
    body = upload(client, [ticket(), ticket(ticket_id="TCK-000003")]).json()
    assert body["already_imported"] == 1
    assert body["imported"] == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Ticket)) == 3


def test_agents_are_stored_once(client):
    upload(client, [ticket(ticket_id=f"TCK-{n:06d}") for n in range(1, 4)])
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Agent)) == 1


def test_columns_can_be_in_any_order_and_case(client):
    columns = ["Priority", "TICKET_ID", "agent", "category", "root_cause", "opened_at", "closed_at"]
    row = {k: v for k, v in ticket().items()}
    row["Priority"], row["TICKET_ID"] = row.pop("priority"), row.pop("ticket_id")
    body = upload(client, content=to_csv([row], columns)).json()
    assert body["imported"] == 1


def test_excel_bom_is_handled(client):
    body = upload(client, content=b"\xef\xbb\xbf" + to_csv([ticket()])).json()
    assert body["imported"] == 1


def test_missing_columns_return_422(client):
    response = upload(client, content=b"ticket_id,agent\nTCK-000001,Ana\n")
    assert response.status_code == 422
    assert "category" in response.json()["detail"]


def test_empty_file_returns_422(client):
    assert upload(client, content=b"").status_code == 422


def test_non_utf8_file_returns_422(client):
    assert upload(client, content="ticket_id\nTCK-é".encode("latin-1")).status_code == 422


def test_file_over_size_limit_returns_413(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 100)
    assert upload(client, [ticket(ticket_id=f"TCK-{n:06d}") for n in range(1, 10)]).status_code == 413


def test_error_list_is_capped_but_counts_are_complete(client):
    rows = [ticket(ticket_id=f"BAD-{n}") for n in range(150)]
    body = upload(client, rows).json()
    assert body["invalid"] == 150
    assert len(body["errors"]) == 100


def test_import_history_lists_uploads_newest_first(client):
    upload(client, [ticket()], filename="first.csv")
    upload(client, [ticket(ticket_id="TCK-000002")], filename="second.csv")
    history = client.get("/imports").json()
    assert [h["filename"] for h in history] == ["second.csv", "first.csv"]
    assert history[0]["imported"] == 1


def test_sample_file_end_to_end(client):
    body = upload(client, content=SAMPLE.read_bytes(), filename="sample_tickets.csv").json()
    assert body["total_rows"] == 5000
    assert body["imported"] + body["duplicates"] + body["invalid"] == 5000
    assert body["duplicates"] > 100
    assert 0 < body["invalid"] < 150
    assert body["imported"] > 4700


def test_health(anon):
    assert anon.get("/health").json() == {"status": "ok"}
