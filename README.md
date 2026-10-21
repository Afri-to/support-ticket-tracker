# Support Ticket Tracker

![ci](https://github.com/Afri-to/support-ticket-tracker/actions/workflows/ci.yml/badge.svg)

A full-stack app that imports support tickets from CSV exports, cleans them (validation and deduplication), and shows weekly KPIs on a dashboard. It uses **fake, generated data only**.

> Status: in progress. See the roadmap below.

![Dashboard](docs/dashboard.png)

## Dashboard

- **Filters** for week and agent sit in one row above everything they affect.
- **Headline numbers:** tickets, still open, average and median time to resolve.
- **Four charts:** tickets opened and closed per week, average time to resolve per week, top root causes, and tickets per agent. Charts that compare weeks or agents keep showing all of them and highlight your selection instead of hiding the rest.
- **Every chart has a "Show table" view**, so no number is locked inside a picture.
- **Ticket table** with search (debounced, so it waits until you stop typing) and paging.
- **CSV import** that reports exactly what happened to each row.
- Light and dark mode, keyboard focus styles, works on phones.

## Accounts and the demo

- **Create an account** with an email and password, then import your own CSV. Every query is limited to the signed-in user, so nobody sees anyone else's tickets (tests check this directly).
- **Explore the demo** signs you in to a shared, read-only account already filled with the 4,789 sample tickets, so you can try the dashboard without signing up.
- Passwords are hashed with scrypt and a random salt per user. Sessions are random tokens in an `HttpOnly`, `SameSite=Lax` cookie, and the database stores only a SHA-256 hash of each token. A wrong email and a wrong password get the same answer, so the login form doesn't reveal which emails have accounts.

## Tech stack

Backend: Python 3.12 · FastAPI · PostgreSQL · SQLAlchemy · pytest · GitHub Actions
Frontend: React · TypeScript · Vite · Recharts · Vitest + Testing Library

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

## KPIs

| Endpoint | Returns |
|---|---|
| `GET /kpis/summary` | Total and open tickets, average and median hours to resolve |
| `GET /kpis/weekly` | Tickets opened and closed per week (weeks start Monday), average hours to resolve |
| `GET /kpis/root-causes` | Most common root causes with their share of all tickets (`limit`, default 5) |
| `GET /kpis/agents` | Tickets, open tickets and average hours to resolve per agent |
| `GET /agents` | Agents for the dashboard filter |

All KPI endpoints take the same optional filters: `agent_id`, `from` and `to` (dates, inclusive). The queries are plain SQL in [`backend/app/kpis.py`](backend/app/kpis.py), using `COUNT(*) FILTER`, `PERCENTILE_CONT` for the median, `DATE_TRUNC('week', ...)` and a window function for each root cause's share. Values are always bound parameters.

### Schema

```
agents (id, name)            categories (id, name)
   \                             /
    tickets (ticket_id UNIQUE, agent_id, category_id, root_cause, priority,
             opened_at, closed_at  CHECK closed_at >= opened_at, import_id)
                                  |
                       imports (filename, created_at, row counts)
```

## Run it locally

```bash
# API (needs PostgreSQL with a "tickets" database)
cd backend && uvicorn app.main:app --reload --port 8000

# Dashboard, in a second terminal (forwards /api to the API)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 and import `data/sample_tickets.csv`.

## Run the tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v

cd ../frontend && npm test

# End-to-end (real browser, real API, real database "tickets_e2e")
VITE_API_URL="" npm run build && npm run e2e
```

The Playwright tests create an account, import the sample CSV, check the import summary and the dashboard, filter by agent, search the table, re-upload the same file (nothing changes), sign out and back in, and explore the read-only demo. They caught a real bug: the import summary disappeared after a user's first import.

Tests need PostgreSQL with a `tickets_test` database (set `TEST_DATABASE_URL` if your connection differs from `postgresql+psycopg://postgres:postgres@localhost:5432/tickets_test`). CI runs them against a PostgreSQL service container.

## Roadmap

- [x] Fake dataset generator with deliberately messy rows
- [x] CSV upload: validate, deduplicate, and report what was imported
- [x] Database schema and KPI queries (weekly volume, time to resolve, root causes, per-agent volume)
- [x] React dashboard with week and agent filters
- [x] Login so each user sees only their own uploads, plus a read-only demo account
- [x] End-to-end tests with Playwright
- [ ] Live deployment
