# Homework 02: GrabTab — Expense Splitter

**Grab it. Add it. Share it.**

GrabTab is a lightweight shared-household shopping list and expense splitter.
When someone buys a list item, it automatically becomes a shared expense.

## MVP features

- Shared shopping list, showing who added each item
- Buy-to-expense flow: enter the price and split it across household members
- Direct expenses with selectable equal-split participants
- Owner-only expense editing and deletion
- Net balances, pairwise debts, and debt settlement records
- Invite code/link display for the household

## Tech stack

- Frontend: dependency-free HTML, CSS, and JavaScript
- Backend: FastAPI
- Data access: SQLAlchemy
- Default database: SQLite (`grabtab.db`), seeded automatically on first start
- Tests: pytest and FastAPI TestClient

## Run locally

Open two PowerShell terminals from this directory.

In the first terminal, install the locked backend dependencies and start the API:

```powershell
uv sync
uv run uvicorn backend.app:app --reload --port 8000
```

In the second terminal, serve the frontend:

```powershell
cd frontend
py -m http.server 5173
```

Open `http://localhost:5173` to use the app. API documentation is available at
`http://localhost:8000/docs`.

The development backend uses `mock-anna` as the frontend's default Bearer token.
It also recognizes `mock-ben` and `mock-clara`.

## Database configuration

The default SQLite database is created at `grabtab.db`. It is ignored by Git.
The persistence layer is database-agnostic through SQLAlchemy: set
`DATABASE_URL` to use another supported database and install its Python driver.

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost/grabtab"
uv run uvicorn backend.app:app --reload --port 8000
```

## Tests

Run the endpoint suite with:

```powershell
uv run pytest
```

## Project layout

- `frontend/` — browser UI and centralized HTTP API client
- `backend/` — FastAPI routes, SQLAlchemy models, and repository
- `tests/` — API and persistence tests
- `_docs/` — product and backend implementation specifications
- `openapi.yaml` — API contract
