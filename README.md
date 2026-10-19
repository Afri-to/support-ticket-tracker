# Support Ticket Tracker

![ci](https://github.com/Afri-to/support-ticket-tracker/actions/workflows/ci.yml/badge.svg)

A full-stack app that imports support tickets from CSV exports, cleans them (validation and deduplication), and shows weekly KPIs on a dashboard. It uses **fake, generated data only**.

> Status: in progress. See the roadmap below.

## Tech stack

Backend: Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy · pytest · GitHub Actions
Frontend (coming next): React · TypeScript · Vite

## Sample data

`data/sample_tickets.csv` has 5,000 fake tickets made by `backend/scripts/generate_tickets.py` with Faker. About 3% of rows are exact duplicates and about 1% have one problem each (missing agent, unknown priority, bad date, closed before opened, malformed ID), so the importer has real cleanup to do.

```bash
cd backend
python -m scripts.generate_tickets --rows 5000 --out ../data/sample_tickets.csv
```

The same `--seed` always produces the same file.

## Importing a CSV

`POST /imports` takes a CSV upload and returns what happened to every row. Uploading the sample file gives:

```json
{"total_rows": 5000, "imported": 4789, "duplicates": 159, "already_imported": 0, "invalid": 52,
 "errors": [{"line": 766, "ticket_id": "TCK-000745", "problems": [{"code": "UNKNOWN_PRIORITY", "message": "'???' isn't one of Low, Medium, High, Critical."}]}, "..."]}
```

Each row goes through these checks, in order:

| Check | Result |
|---|---|
| Missing field, malformed ticket ID, unknown priority, bad date, closed before opened | Rejected, with the line number and every reason (`invalid`) |
| Exact copy of an earlier row in the same file | Dropped quietly (`duplicates`) |
| Same ticket ID as an earlier row but different values | Rejected as `CONFLICTING_DUPLICATE`; the first row is kept |
| Ticket ID already imported from an earlier file | Skipped (`already_imported`), so re-uploading a file is safe |

Columns can come in any order and any letter case, an Excel UTF-8 BOM is handled, and files over 5 MB are refused. `GET /imports` lists past uploads with their counts.

## Run the tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

Tests need PostgreSQL with a `tickets_test` database (set `TEST_DATABASE_URL` if your connection differs from `postgresql+psycopg://postgres:postgres@localhost:5432/tickets_test`). CI runs them against a PostgreSQL service container.

## Roadmap

- [x] Fake dataset generator with deliberately messy rows
- [x] CSV upload: validate, deduplicate, and report what was imported
- [ ] Database schema and KPI queries (weekly volume, time to resolve, root causes, per-agent volume)
- [ ] React dashboard with week and agent filters
- [ ] Login so each user sees only their own uploads
- [ ] End-to-end test with Playwright
- [ ] Live deployment
