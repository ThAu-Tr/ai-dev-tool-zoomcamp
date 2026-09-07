# Shared Household Chores

Homework 01 for AI Dev Tool Zoomcamp.

Manage shared chores, record member contributions, and grow cosmetic personal gardens. The initial version serves one household with predefined members and no login.

## Project documents

- [Product plan](_docs/plan.md)
- [Architecture](_docs/architecture.md)
- [Implementation backlog](_docs/backlog.md)

Selected stack: Python 3.14.7, Django 6.1.1, SQLite, Django templates/forms, and plain CSS/SVG. The shipped MVP serves one shared household with predefined members and no login.

## Local setup

Install `uv` and Git first. Run all commands below from `01-shared-household-chores/`, not the course repository root.

```sh
uv sync
uv run python manage.py migrate
uv run python manage.py setup_members
uv run python manage.py runserver
```

`uv sync` installs the pinned Python runtime when needed, creates `.venv/`, and installs dependencies from `uv.lock`. No environment activation or separate SQLite installation is required. Running `migrate` prepares the local SQLite database. Run `setup_members` after migrating to create the predefined members Alex, Sam, and Jamie in display order. The command is safe to repeat: it creates no duplicates and never changes existing member data. If an existing member conflicts with a required name or display order, it exits with an error and leaves all members unchanged.

Open http://127.0.0.1:8000/ to open the household page. Stop the server with Ctrl+C.

The application has three public pages:

- **Household** (`/`) — current monthly scores, active chores, due status, completion attribution, and add/edit/delete controls.
- **Member** (`/members/<id>/`) — one member's monthly points, lifetime XP, completion history, and personal garden.
- **Neighborhood** (`/neighborhood/`) — all predefined members' gardens together, with links to their member pages.

There is deliberately no login or account ownership. Anyone who can access the app can view every member page and use household actions. When a chore is completed, the person using the app selects the member who did the work; that selection records attribution and does not authenticate the user.

## Verification

```sh
uv run python manage.py test
uv run python manage.py test household.tests.test_home
uv run python manage.py check
```

The test suite covers the household data journey, validation, scheduling, atomic and concurrent completion, scores, history preservation, member pages, gardens, and the neighborhood view. The smoke test also verifies that the homepage returns HTTP 200 without login.

## Project structure

- `config/` — Django settings, root URLs, and WSGI/ASGI entry points.
- `household/` — application views, templates, and tests.
- `pyproject.toml` and `uv.lock` — declared and locked dependencies.
- `.python-version` — pinned Python runtime.

Settings are for local development only: debug mode is enabled, the secret key is generated per process, and the household timezone is Europe/Berlin. Do not use Django's development server or these settings for production. Production configuration, hosting, and persistent-storage decisions are tracked in [issue 19](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp/issues/19) and [issue 20](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp/issues/20); database backup and restore are tracked in [issue 21](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp/issues/21). Those operational procedures must be finalized before a production deployment. Virtual environments, secrets, local SQLite files, and backup artifacts are excluded by the course repository's `.gitignore`.

## Operations handover

The repository currently documents local development only. Once issues 19–21 are complete, link their finalized provider/deployment and SQLite backup/restore documents here and follow those procedures for production operations. Until then, do not treat `runserver`, the generated development secret key, or the repository-local `db.sqlite3` as a production arrangement. A no-login deployment must be access-controlled at the hosting/network boundary because every reachable user can perform household actions.

## Work tracking

Issues use `homework:01` and either `scope:mvp` or `scope:post-mvp`. Initial delivery tasks belong to the `HW01 — MVP submission` milestone; optional improvements remain outside that milestone until scheduled.

See the backlog for the next implementation tasks.
