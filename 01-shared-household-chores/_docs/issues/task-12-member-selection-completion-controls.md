# Task 12: Add member selection and completion controls

## Goal

Add member selection dropdown and completion form controls to eligible chores on the household page, submit via CSRF-protected POST to `household:chore_complete`, invoke the atomic completion operation, and redirect with clear flash messages for success, stale submissions, or errors.

## Acceptance criteria

- [ ] Each eligible active chore (DUE or OVERDUE) on the household home page renders a completion form.
- [ ] The completion form:
  - targets `household:chore_complete` for that chore (`chores/<int:pk>/complete/`),
  - includes a CSRF token,
  - has a clearly labeled member dropdown (`<select name="member">`) populated with all household members ordered by display order,
  - has a hidden input `completion_version` carrying `chore.completion_version`,
  - has a submit button labeled "Complete" (or similar clear action).
- [ ] Ineligible chores (`NOT_YET_DUE`) indicate they are not yet eligible and do not render an active completion button.
- [ ] A POST request to `chores/<int:pk>/complete/` enforces CSRF protection.
- [ ] If required POST parameters (`member`, `completion_version`) are missing or invalid, an error flash message is set and the user is redirected to `household:home`.
- [ ] On successful completion, a success flash message is set (e.g. `Completed "<chore name>" for <member name>.`) and redirects to `household:home`.
- [ ] On stale/repeated submission (version mismatch), an informative warning/message is set (e.g. `This chore occurrence has already been completed or modified.`) and redirects to `household:home` without awarding duplicate points.
- [ ] If the chore is inactive, not found, or not yet due, an appropriate error/warning message is displayed and redirects to `household:home`.
- [ ] GET request to `chores/<int:pk>/complete/` redirects to `household:home`.

## Out of scope

- Calculating and updating monthly score tables / leaderboard (handled in Task 13).
- Member profile pages (handled in Task 14).
- Garden visual rendering (handled in Tasks 15 & 16).

## Constraints

- Files: `household/urls.py`, `household/views.py`, `household/templates/household/home.html`, `household/tests/test_chore_complete_view.py`.
- Preserve the no-login attribution model: member selection is attribution, not authentication.
- Follow Django POST/Redirect/GET pattern and message framework.

## QA: PASS

- [x] Each eligible active chore renders a completion form — PASS
- [x] Completion form targets `chore_complete`, includes CSRF token, member dropdown, hidden completion_version, and Complete button — PASS
- [x] Ineligible chores indicate they are not yet eligible and do not render active completion button — PASS
- [x] POST request enforces CSRF protection — PASS
- [x] Missing or invalid POST parameters set error message and redirect to home — PASS
- [x] Successful completion sets success message and redirects to home — PASS
- [x] Stale/repeated submission sets warning message and prevents duplicate points — PASS
- [x] Inactive, not found, or not yet due chore sets appropriate message and redirects to home — PASS
- [x] GET request to complete endpoint redirects to home — PASS

Tests: `.venv\Scripts\python.exe manage.py test`, 118 passed, 0 failed.

Status: CLOSED
