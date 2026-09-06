# Task 9: Add chore deletion with history preservation

## Goal

Provide a deletion confirmation page that marks a chore as inactive via POST, removes it from active chore lists, preserves all completion history, and redirects to the household home page.

## Acceptance criteria

- [ ] A "Delete chore" link is available for each active chore (e.g. on the chore edit page or household chore card) linking to `household:chore_delete` (`chores/<int:pk>/delete/`).
- [ ] A GET request to `chores/<int:pk>/delete/` for an active chore renders a confirmation page showing the chore name, a cancel link back to household home, and a submit button to confirm deletion.
- [ ] A GET request to `chores/<int:pk>/delete/` makes no modifications to the chore or any completion records.
- [ ] A GET request to `chores/<int:pk>/delete/` for a non-existent or inactive chore returns HTTP 404.
- [ ] A POST request to `chores/<int:pk>/delete/` requires CSRF protection.
- [ ] A successful POST request sets the chore's `is_active` field to `False` and saves it.
- [ ] A successful POST request does not delete or modify any existing `Completion` records associated with the chore.
- [ ] A successful POST request redirects to `household:home` with a visible success notification (e.g. `Chore "<name>" deleted.`).
- [ ] After deletion, the chore no longer appears in the active chore list on `household:home`.
- [ ] After deletion, a new chore with the same name can be created without triggering a unique name conflict.
- [ ] A POST request to `chores/<int:pk>/delete/` for an inactive chore returns HTTP 404.

## Out of scope

- Restoring or un-deleting inactive chores from the UI (moved to post-MVP).
- Hard-deleting chore records or purging history from the database (excluded by architecture).
- Separate audit log table for deletions (excluded by architecture).

## Constraints

- Files: `household/urls.py`, `household/views.py`, `household/templates/household/chore_confirm_delete.html`, `household/templates/household/chore_form.html` (or `home.html`), `household/tests/test_chore_delete.py`.
- Keep business logic in Python, outside templates.
- Follow Django's POST/Redirect/GET pattern and messages framework.

## QA: PASS

- [x] A "Delete chore" link is available for each active chore linking to `household:chore_delete` (`chores/<int:pk>/delete/`) — PASS
- [x] A GET request to `chores/<int:pk>/delete/` for an active chore renders a confirmation page showing the chore name, cancel link back to household home, and submit button — PASS
- [x] A GET request to `chores/<int:pk>/delete/` makes no modifications to the chore or any completion records — PASS
- [x] A GET request to `chores/<int:pk>/delete/` for a non-existent or inactive chore returns HTTP 404 — PASS
- [x] A POST request to `chores/<int:pk>/delete/` requires CSRF protection — PASS
- [x] A successful POST request sets the chore's `is_active` field to `False` and saves it — PASS
- [x] A successful POST request does not delete or modify any existing `Completion` records associated with the chore — PASS
- [x] A successful POST request redirects to `household:home` with a visible success notification — PASS
- [x] After deletion, the chore no longer appears in the active chore list on `household:home` — PASS
- [x] After deletion, a new chore with the same name can be created without triggering a unique name conflict — PASS
- [x] A POST request to `chores/<int:pk>/delete/` for an inactive chore returns HTTP 404 — PASS

Tests: `.venv\Scripts\python.exe manage.py test`, 95 passed, 0 failed.

Status: CLOSED
