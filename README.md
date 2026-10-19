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

## Run the tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

## Roadmap

- [x] Fake dataset generator with deliberately messy rows
- [ ] CSV upload: validate, deduplicate, and report what was imported
- [ ] Database schema and KPI queries (weekly volume, time to resolve, root causes, per-agent volume)
- [ ] React dashboard with week and agent filters
- [ ] Login so each user sees only their own uploads
- [ ] End-to-end test with Playwright
- [ ] Live deployment
