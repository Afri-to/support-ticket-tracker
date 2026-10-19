import csv
import re
from datetime import datetime

from scripts.generate_tickets import FIELDS, ROOT_CAUSES, generate, write_csv


def test_generates_requested_number_of_rows():
    assert len(generate(500)) == 500


def test_same_seed_gives_same_data():
    assert generate(200, seed=7) == generate(200, seed=7)
    assert generate(200, seed=7) != generate(200, seed=8)


def test_includes_exact_duplicates():
    rows = generate(2000)
    keys = [tuple(r.values()) for r in rows]
    assert len(keys) - len(set(keys)) > 20


def test_includes_some_broken_rows():
    rows = generate(2000)
    broken = [
        r for r in rows
        if not r["agent"]
        or r["priority"] not in {"Low", "Medium", "High", "Critical"}
        or not re.fullmatch(r"TCK-\d{6}", r["ticket_id"])
    ]
    assert broken, "expected some deliberately messy rows"


def test_clean_rows_are_consistent():
    for row in generate(1000):
        if row["category"] in ROOT_CAUSES and row["root_cause"] not in ROOT_CAUSES[row["category"]]:
            raise AssertionError(row)


def test_write_csv_has_header_and_rows(tmp_path):
    path = tmp_path / "t.csv"
    write_csv(generate(10), path)
    with path.open() as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS
        rows = list(reader)
    assert len(rows) == 10
    datetime.fromisoformat(rows[0]["opened_at"])
