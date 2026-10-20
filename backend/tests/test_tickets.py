import pytest

from tests.conftest import ticket, upload


@pytest.fixture
def loaded(client):
    rows = [
        ticket(ticket_id="TCK-000001", agent="Ana Torres", category="Network", root_cause="Wi-Fi dropout",
               opened_at="2026-07-06T09:00", closed_at="2026-07-06T11:30"),
        ticket(ticket_id="TCK-000002", agent="Ben Ortiz", category="Printer", root_cause="Paper jam",
               opened_at="2026-07-07T09:00", closed_at=""),
        ticket(ticket_id="TCK-000003", agent="Ana Torres", category="Printer", root_cause="Out of toner 50%",
               opened_at="2026-07-08T09:00", closed_at="2026-07-08T10:00"),
    ]
    upload(client, rows)
    return client


def ids(response):
    return [t["ticket_id"] for t in response.json()["items"]]


def test_lists_newest_first_with_total(loaded):
    response = loaded.get("/tickets")
    assert response.json()["total"] == 3
    assert ids(response) == ["TCK-000003", "TCK-000002", "TCK-000001"]


def test_row_fields(loaded):
    first = loaded.get("/tickets", params={"search": "TCK-000001"}).json()["items"][0]
    assert first["agent"] == "Ana Torres"
    assert first["category"] == "Network"
    assert first["priority"] == "High"
    assert first["resolve_hours"] == "2.5"


def test_open_ticket_has_no_resolve_time(loaded):
    item = loaded.get("/tickets", params={"search": "TCK-000002"}).json()["items"][0]
    assert item["closed_at"] is None and item["resolve_hours"] is None


@pytest.mark.parametrize("term, expected", [
    ("ana", ["TCK-000003", "TCK-000001"]),     # agent, any case
    ("printer", ["TCK-000003", "TCK-000002"]),  # category
    ("jam", ["TCK-000002"]),                    # root cause
    ("000001", ["TCK-000001"]),                 # ticket id
    ("50%", ["TCK-000003"]),                    # % is literal, not a wildcard
    ("   ", ["TCK-000003", "TCK-000002", "TCK-000001"]),  # blank = no search
])
def test_search(loaded, term, expected):
    assert ids(loaded.get("/tickets", params={"search": term})) == expected


def test_wildcard_characters_do_not_match_everything(loaded):
    assert loaded.get("/tickets", params={"search": "_"}).json()["total"] == 0


def test_paging(loaded):
    page = loaded.get("/tickets", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 3
    assert [t["ticket_id"] for t in page["items"]] == ["TCK-000001"]
    assert loaded.get("/tickets", params={"limit": 101}).status_code == 422


def test_search_combines_with_filters(loaded):
    body = loaded.get("/tickets", params={"search": "printer", "to": "2026-07-07"}).json()
    assert body["total"] == 1
