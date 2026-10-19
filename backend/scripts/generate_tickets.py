"""Generate a fake support-ticket CSV for testing the importer.

Every value is invented with Faker. Some rows are deliberately broken
(duplicates, bad dates, missing fields, unknown priorities) so the importer
has real cleanup work to do, like a messy export from a ticketing system.

Usage:
    python -m scripts.generate_tickets --rows 5000 --out ../data/sample_tickets.csv
"""

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

FIELDS = ["ticket_id", "agent", "category", "root_cause", "priority", "opened_at", "closed_at"]

# Each category has its own set of root causes, like a real support taxonomy.
ROOT_CAUSES = {
    "Hardware": ["Failed disk", "Battery worn out", "Loose cable", "Overheating"],
    "Network": ["Wi-Fi dropout", "DNS misconfiguration", "Firewall rule", "Switch port down"],
    "Account Access": ["Password expired", "Account locked", "MFA reset", "Missing permissions"],
    "Software": ["Failed update", "Licence expired", "Crash on launch", "Wrong version installed"],
    "Printer": ["Paper jam", "Driver missing", "Out of toner", "Queue stuck"],
    "Barcode Scanner": ["Not pairing", "Battery worn out", "Firmware outdated", "Damaged lens"],
}
PRIORITIES = ["Low", "Medium", "High", "Critical"]
PRIORITY_WEIGHTS = [40, 35, 18, 7]
# Typical hours to resolve by priority (mean); higher priority closes faster.
RESOLVE_HOURS = {"Low": 40, "Medium": 24, "High": 10, "Critical": 4}

DUPLICATE_RATE = 0.03  # exact copies of an earlier row
INVALID_RATE = 0.01  # rows with one problem each
OPEN_RATE = 0.05  # tickets still open (no closed_at)


def make_ticket(fake: Faker, rng: random.Random, number: int, agents: list[str], start: datetime, days: int) -> dict:
    category = rng.choice(list(ROOT_CAUSES))
    priority = rng.choices(PRIORITIES, PRIORITY_WEIGHTS)[0]
    opened = start + timedelta(minutes=rng.randrange(days * 24 * 60))
    closed = None
    if rng.random() > OPEN_RATE:
        hours = max(0.25, rng.expovariate(1 / RESOLVE_HOURS[priority]))
        closed = opened + timedelta(hours=hours)
    return {
        "ticket_id": f"TCK-{number:06d}",
        "agent": rng.choice(agents),
        "category": category,
        "root_cause": rng.choice(ROOT_CAUSES[category]),
        "priority": priority,
        "opened_at": opened.isoformat(timespec="minutes"),
        "closed_at": closed.isoformat(timespec="minutes") if closed else "",
    }


def break_row(row: dict, rng: random.Random) -> dict:
    """Introduce exactly one realistic problem into a copy of the row."""
    row = dict(row)
    problem = rng.choice(["no_agent", "bad_priority", "bad_date", "closed_before_opened", "bad_id"])
    if problem == "no_agent":
        row["agent"] = ""
    elif problem == "bad_priority":
        row["priority"] = rng.choice(["Urgent", "P1", "???"])
    elif problem == "bad_date":
        row["opened_at"] = rng.choice(["31/02/2026", "yesterday", ""])
    elif problem == "closed_before_opened":
        opened = datetime.fromisoformat(row["opened_at"])
        row["closed_at"] = (opened - timedelta(hours=3)).isoformat(timespec="minutes")
    else:
        row["ticket_id"] = row["ticket_id"].replace("TCK-", "TKT")
    return row


def generate(rows: int, seed: int = 42, agents_count: int = 12, days: int = 120) -> list[dict]:
    """Return `rows` CSV rows. The same seed always gives the same data."""
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)
    agents = sorted({fake.name() for _ in range(agents_count * 2)})[:agents_count]
    start = datetime(2026, 6, 1, 8, 0)

    out: list[dict] = []
    number = 1
    while len(out) < rows:
        roll = rng.random()
        if out and roll < DUPLICATE_RATE:
            out.append(dict(rng.choice(out)))
        elif roll < DUPLICATE_RATE + INVALID_RATE:
            out.append(break_row(make_ticket(fake, rng, number, agents, start, days), rng))
            number += 1
        else:
            out.append(make_ticket(fake, rng, number, agents, start, days))
            number += 1
    return out


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("../data/sample_tickets.csv"))
    args = parser.parse_args()
    write_csv(generate(args.rows, args.seed), args.out)
    print(f"Wrote {args.rows} rows to {args.out}")


if __name__ == "__main__":
    main()
