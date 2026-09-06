# Task 11: Verify competing completions and handle SQLite contention

## Goal

Ensure simultaneous completion attempts cannot award points twice or leave partial database state, implement bounded SQLite lock contention handling, and verify concurrent behavior with a focused multi-threaded test against a file-backed SQLite database.

## Acceptance criteria

- [ ] `CompletionStatus.LOCKED` (or recoverable outcome) is added to `household/completion.py` for bounded SQLite lock contention.
- [ ] `complete_chore` handles SQLite `OperationalError` lock/busy errors with bounded retry (e.g. up to 3 attempts with brief backoff) and returns `CompletionStatus.LOCKED` if contention persists, without swallowing unrelated `OperationalError`s.
- [ ] A dedicated concurrency test suite (`household/tests/test_completion_concurrency.py`) exercises simultaneous completion attempts for the same chore across multiple threads with independent database connections against a file-backed SQLite database.
- [ ] In simultaneous competing attempts for the same chore occurrence, exactly one attempt succeeds and awards points.
- [ ] No competing attempt creates a duplicate `Completion` record or awards duplicate points.
- [ ] No partial state is left if an attempt encounters contention or version mismatch (chore version and due date match completion count).
- [ ] The outcomes and error handling of `complete_chore` are documented for its UI caller in `household/completion.py`.

## Out of scope

- Multi-process distributed locking (unnecessary for single SQLite instance).
- Postgres row-level locking (outside single-household SQLite stack).
- Building the UI completion form/view (handled in Task 12).

## Constraints

- Files: `household/completion.py`, `household/tests/test_completion_concurrency.py`.
- Must handle SQLite lock errors (`database is locked` / `busy`) specifically.
- Must ensure test cleanly tears down any temporary file-backed databases.

## QA: PASS

- [x] `CompletionStatus.LOCKED` is added to `household/completion.py` for bounded SQLite lock contention — PASS
- [x] `complete_chore` handles SQLite `OperationalError` lock/busy errors with bounded retry and returns `CompletionStatus.LOCKED` if contention persists, without swallowing unrelated `OperationalError`s — PASS
- [x] Dedicated concurrency test suite (`household/tests/test_completion_concurrency.py`) exercises simultaneous completion attempts for the same chore across multiple threads with independent database connections — PASS
- [x] In simultaneous competing attempts for the same chore occurrence, exactly one attempt succeeds and awards points — PASS
- [x] No competing attempt creates a duplicate `Completion` record or awards duplicate points — PASS
- [x] No partial state is left if an attempt encounters contention or version mismatch — PASS
- [x] Outcomes and error handling of `complete_chore` are documented for its UI caller in `household/completion.py` — PASS

Tests: `.venv\Scripts\python.exe manage.py test`, 108 passed, 0 failed.

Status: CLOSED
