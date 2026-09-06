# Task 10: Implement atomic chore completion

## Goal

Implement a shared atomic completion service function that validates member, active chore, eligibility, and expected version, conditionally advances the chore's due date and completion version, and records the completion in one SQLite-compatible transaction with clear outcomes.

## Acceptance criteria

- [ ] A completion function `complete_chore(...)` is defined in `household/completion.py` with structured outcome types (`CompletionStatus`, `CompletionResult`).
- [ ] Attempting to complete with an unknown member or non-existent chore returns a `NOT_FOUND` outcome.
- [ ] Attempting to complete an inactive (`is_active=False`) chore returns an `INACTIVE_CHORE` outcome without creating a completion or changing chore state.
- [ ] Attempting to complete a chore that is `NOT_YET_DUE` (based on `Europe/Berlin` local date at `completed_at`) returns an `INELIGIBLE` outcome without creating a completion or changing chore state.
- [ ] Attempting to complete a chore with a stale `expected_version` (where `chore.completion_version != expected_version`) returns a `STALE_VERSION` outcome without creating a completion or changing chore state.
- [ ] A valid completion atomically:
  - advances `chore.completion_version` by 1,
  - advances `chore.next_due_date` using `calculate_next_due_date`,
  - creates a `Completion` record with `member`, `chore`, `completed_at`, `awarded_points = chore.points`, `chore_name_snapshot = chore.name`, and `completed_version = expected_version`,
  - commits both changes together in one transaction and returns `CompletionStatus.SUCCESS`.
- [ ] If an error occurs during completion creation, the transaction rolls back so neither the chore's version/due date nor any completion record is persisted.
- [ ] Repeating a completion submission with the same version that previously succeeded returns `STALE_VERSION` and creates no duplicate points or records.

## Out of scope

- Direct multi-threaded SQLite lock contention testing (handled in Task 11).
- Exposing the completion operation to the web UI / forms (handled in Task 12).
- Calculating and displaying monthly totals or garden stages (handled in Tasks 13 & 16).

## Constraints

- Files: `household/completion.py`, `household/tests/test_completion_operation.py`.
- Must use `django.db.transaction.atomic`.
- Must use conditional version updates (`update(completion_version=expected_version + 1, ...)`) compatible with SQLite.
- All timestamps must be timezone-aware (Europe/Berlin aware or UTC aware converted appropriately).

## QA: PASS

- [x] A completion function `complete_chore(...)` is defined in `household/completion.py` with structured outcome types (`CompletionStatus`, `CompletionResult`) — PASS
- [x] Attempting to complete with an unknown member or non-existent chore returns a `NOT_FOUND` outcome — PASS
- [x] Attempting to complete an inactive chore returns an `INACTIVE_CHORE` outcome without creating a completion or changing chore state — PASS
- [x] Attempting to complete a chore that is `NOT_YET_DUE` returns an `INELIGIBLE` outcome without creating a completion or changing chore state — PASS
- [x] Attempting to complete a chore with a stale `expected_version` returns a `STALE_VERSION` outcome without creating a completion or changing chore state — PASS
- [x] A valid completion atomically advances completion_version, advances next_due_date, creates Completion record, commits both in one transaction, and returns SUCCESS — PASS
- [x] If an error occurs during completion creation, transaction rolls back completely — PASS
- [x] Repeating a completion submission with the same version returns STALE_VERSION and creates no duplicate points or records — PASS

Tests: `.venv\Scripts\python.exe manage.py test`, 105 passed, 0 failed.

Status: CLOSED
