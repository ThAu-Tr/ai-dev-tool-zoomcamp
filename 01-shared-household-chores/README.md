# Shared Household Chores

Homework 01 for AI Dev Tool Zoomcamp.

Manage shared chores, record member contributions, and grow cosmetic personal gardens. The initial version serves one household with predefined members and no login.

## Project documents

- [Product plan](_docs/plan.md)
- [Architecture](_docs/architecture.md)
- [Implementation backlog](_docs/backlog.md)

Selected stack: Python 3.14.7, Django 6.1.1, SQLite, Django templates/forms, and plain CSS/SVG. The initial scaffold serves a placeholder homepage; household features are not implemented yet.

## Local setup

Install `uv` and Git first. Run all commands below from `01-shared-household-chores/`, not the course repository root.

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py setup_members
uv run python manage.py runserver
```

`uv sync` installs the pinned Python runtime when needed, creates `.venv/`, and installs dependencies from `uv.lock`. No environment activation or separate SQLite installation is required. Running `migrate` prepares the local SQLite database. Run `setup_members` after migrating to create the predefined members Alex, Sam, and Jamie in display order. The command is safe to repeat: it creates no duplicates and never changes existing member data. If an existing member conflicts with a required name or display order, it exits with an error and leaves all members unchanged.

Open http://127.0.0.1:8000/ to see the placeholder page. Stop the server with Ctrl+C.

## Verification

```sh
uv run python manage.py test
uv run python manage.py test household.tests.test_home
uv run python manage.py check
```

The smoke test verifies that the homepage returns HTTP 200 and renders the expected template and heading without login.

## Project structure

- `config/` — Django settings, root URLs, and WSGI/ASGI entry points.
- `household/` — application views, templates, and tests.
- `pyproject.toml` and `uv.lock` — declared and locked dependencies.
- `.python-version` — pinned Python runtime.

Settings are for local development only: debug mode is enabled, the secret key is generated per process, and the household timezone is Europe/Berlin. Production configuration is a separate backlog task. Virtual environments, secrets, and local SQLite files are excluded by the course repository's `.gitignore`.

## Work tracking

Issues use `homework:01` and either `scope:mvp` or `scope:post-mvp`. Initial delivery tasks belong to the `HW01 — MVP submission` milestone; optional improvements remain outside that milestone until scheduled.

See the backlog for the next implementation tasks.
