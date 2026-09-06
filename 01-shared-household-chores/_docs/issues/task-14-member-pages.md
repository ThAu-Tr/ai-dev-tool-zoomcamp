# Task 14: Build individual member pages

## Goal

Provide a public household view of an individual member's contributions, scores, and newest-first completion history at `/members/<int:pk>/`, and link to these pages from the household view.

## Acceptance criteria

- [ ] A URL route `household:member_detail` is registered at `members/<int:pk>/`.
- [ ] Unknown member IDs return a 404 response.
- [ ] The member detail page renders using the shared layout (`household/base.html`), with an `<h1>` containing the member's name.
- [ ] The page displays:
  - current monthly points,
  - lifetime XP,
  - garden stage label (from `get_member_scores`).
- [ ] The page lists the member's completion history newest-first (`-completed_at`, `-pk`), showing:
  - chore name snapshot (`chore_name_snapshot`),
  - local completion date/time,
  - awarded points.
- [ ] Completions from inactive (deleted) chores are retained and displayed in history with their snapshot names and awarded points.
- [ ] If the member has no completions, a clear empty-history state is displayed (e.g. `No completions recorded yet.`).
- [ ] The household home page (`/`) links each member's name / score card to their member detail page.
- [ ] A navigation link allows returning to the household home page.

## Out of scope

- Full SVG visual garden artwork rendering (handled in Tasks 15 & 16).
- Neighborhood shared page (handled in Task 16).

## Constraints

- Files: `household/urls.py`, `household/views.py`, `household/templates/household/member_detail.html`, `household/templates/household/home.html`, `household/tests/test_member_detail.py`.
- Keep business logic in Python, outside templates.
- Ensure 404 returned for unknown members using `get_object_or_404`.
