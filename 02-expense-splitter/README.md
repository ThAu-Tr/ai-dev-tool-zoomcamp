# GrabTab

## Backend

Install the locked Python dependencies and start the API:

```powershell
uv sync
uv run uvicorn backend.app:app --reload --port 8000
```

By default the API stores data in `grabtab.db` in the repository root. This is
an SQLite database, created and seeded automatically on first start.

The persistence layer is SQLAlchemy-based. To use another supported database,
set `DATABASE_URL` before starting the API (and install that database's Python
driver). For example:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost/grabtab"
uv run uvicorn backend.app:app --reload --port 8000
```

Run the endpoint tests with:

```powershell
uv run pytest
```
