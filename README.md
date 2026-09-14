# AI Dev Tool Zoomcamp

Course homework and experiments, with one self-contained directory per assignment.

## Homework

| Assignment | Project | Status |
| --- | --- | --- |
| 01 | [Shared Household Chores](01-shared-household-chores/README.md) | Planning complete; implementation pending |
| 02 | [GrabTab — Expense Splitter](02-expense-splitter/README.md) | Full-stack MVP complete |

Each homework owns its dependencies, environment, documentation, and tests. Run project commands from the homework directory; see its README for instructions.

## Homework 02: GrabTab

GrabTab combines a shared shopping list with equal expense splitting: marking a
shopping item as bought creates a household expense automatically. The project
includes a static frontend, FastAPI backend, SQLAlchemy persistence layer, and
pytest endpoint tests. See the [project README](02-expense-splitter/README.md)
for local setup and commands.

## Work tracking

- Homework labels identify ownership, starting with `homework:01`.
- Scope labels distinguish `scope:mvp` from `scope:post-mvp`.
- Submission milestones track scheduled MVP delivery, starting with `HW01 — MVP submission`.
- Post-MVP ideas retain their homework label and remain outside the submission milestone until scheduled.

Use one issue per session-sized task and link implementation pull requests to their issues. Homework documentation lives in each project's `_docs/` directory. GitHub issues track execution status; backlog documents retain the task descriptions.

Future homework can add folders and labels without sharing Python environments or application dependencies. Archived local material is excluded from version control.
