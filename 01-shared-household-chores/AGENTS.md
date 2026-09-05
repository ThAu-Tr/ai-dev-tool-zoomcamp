# Shared Household Chores

Homework 01 in a multi-project course repository. Keep changes within this homework unless the task requires otherwise.

Stack: Python, Django, SQLite, Django templates/forms, and plain CSS/SVG. The MVP has one household, predefined members, and no login.

## Commands

Run from `01-shared-household-chores/`. Use Django's built-in test runner.

- `uv sync` — install dependencies.
- `uv run python manage.py runserver` — start the development server.
- `uv run python manage.py test` — run the whole suite.
- `uv run python manage.py test household.tests.test_home` — run one test module.

## Rules

- Use `_docs/plan.md` for product scope and `_docs/architecture.md` for design decisions; read the relevant sections before implementation.
- Declare dependencies in `pyproject.toml` and commit `uv.lock`. Ask before adding dependencies not already authorized.
- Keep business logic in Python, outside templates. Use Django's built-in test runner.
- Preserve completion history and earned points when editing or deleting chores; prevent duplicate completion awards.
- Never commit secrets, local databases, backups, or virtual environments.
- Run checks relevant to the change and commit regularly at coherent checkpoints. Stage only intended files.
