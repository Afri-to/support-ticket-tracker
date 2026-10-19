"""KPI endpoints checked against small hand-made data where the answers are known."""

import pytest

from tests.conftest import ticket, upload

# Week of Mon 2026-07-06 and week of Mon 2026-07-13.
ROWS = [
    # Ana: 2 tickets in week 1, resolved in 2h and 4h
    ticket(ticket_id="TCK-000001", agent="Ana", root_cause="Wi-Fi dropout", opened_at="2026-07-06T09:00", closed_at="2026-07-06T11:00"),
    ticket(ticket_id="TCK-000002", agent="Ana", root_cause="Wi-Fi dropout", opened_at="2026-07-07T09:00", closed_at="2026-07-07T13:00"),
    # Ben: 1 ticket in week 1 resolved in 6h, 1 open ticket in week 2
    ticket(ticket_id="TCK-000003", agent="Ben", category="Printer", root_cause="Paper jam", opened_at="2026-07-08T10:00", closed_at="2026-07-08T16:00"),
    ticket(ticket_id="TCK-000004", agent="Ben", category="Printer", root_cause="Paper jam", opened_at="2026-07-14T10:00", closed_at=""),
    # Ana: week 2, resolved in 12h, opened on Sunday (still week 2)
    ticket(ticket_id="TCK-000005", agent="Ana", root_cause="DNS misconfiguration", opened_at="2026-07-19T08:00", closed_at="2026-07-19T20:00"),
]


@pytest.fixture
def loaded(client):
    assert upload(client, ROWS).json()["imported"] == 5
    return client


def agent_id(client, name):
    return next(a["id"] for a in client.get("/agents").json() if a["name"] == name)


def test_agents_list_is_alphabetical(loaded):
    assert [a["name"] for a in loaded.get("/agents").json()] == ["Ana", "Ben"]


def test_summary(loaded):
    assert loaded.get("/kpis/summary").json() == {
        "total": 5,
        "open": 1,
        "avg_resolve_hours": "6.0",  # (2 + 4 + 6 + 12) / 4
        "median_resolve_hours": "5.0",  # middle of 2, 4, 6, 12
    }


def test_weekly_groups_by_monday(loaded):
    assert loaded.get("/kpis/weekly").json() == [
        {"week_start": "2026-07-06", "opened": 3, "closed": 3, "avg_resolve_hours": "4.0"},
        {"week_start": "2026-07-13", "opened": 2, "closed": 1, "avg_resolve_hours": "12.0"},
    ]


def test_root_causes_ranked_with_share(loaded):
    body = loaded.get("/kpis/root-causes").json()
    assert body[0] == {"category": "Network", "root_cause": "Wi-Fi dropout", "tickets": 2, "share_pct": "40.0"}
    assert body[1]["root_cause"] == "Paper jam"
    assert sum(float(r["share_pct"]) for r in body) == pytest.approx(100.0)


def test_root_causes_limit(loaded):
    assert len(loaded.get("/kpis/root-causes?limit=1").json()) == 1
    assert loaded.get("/kpis/root-causes?limit=0").status_code == 422


def test_agents_kpis(loaded):
    body = {a["agent"]: a for a in loaded.get("/kpis/agents").json()}
    assert body["Ana"]["tickets"] == 3 and body["Ana"]["open"] == 0
    assert body["Ana"]["avg_resolve_hours"] == "6.0"  # (2 + 4 + 12) / 3
    assert body["Ben"]["tickets"] == 2 and body["Ben"]["open"] == 1
    assert body["Ben"]["avg_resolve_hours"] == "6.0"


def test_filter_by_agent(loaded):
    ben = agent_id(loaded, "Ben")
    summary = loaded.get("/kpis/summary", params={"agent_id": ben}).json()
    assert summary["total"] == 2 and summary["open"] == 1


def test_filter_by_dates_is_inclusive(loaded):
    params = {"from": "2026-07-13", "to": "2026-07-19"}
    weeks = loaded.get("/kpis/weekly", params=params).json()
    assert [w["week_start"] for w in weeks] == ["2026-07-13"]
    assert weeks[0]["opened"] == 2  # includes the ticket opened on the 19th


def test_filters_combine(loaded):
    ana = agent_id(loaded, "Ana")
    body = loaded.get("/kpis/summary", params={"agent_id": ana, "from": "2026-07-13"}).json()
    assert body["total"] == 1


def test_from_after_to_is_rejected(loaded):
    assert loaded.get("/kpis/summary", params={"from": "2026-07-20", "to": "2026-07-01"}).status_code == 422


def test_empty_database(client):
    assert client.get("/kpis/summary").json() == {
        "total": 0, "open": 0, "avg_resolve_hours": None, "median_resolve_hours": None,
    }
    assert client.get("/kpis/weekly").json() == []
