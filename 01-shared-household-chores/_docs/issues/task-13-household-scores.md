# Task 13: Calculate contributions and display household scores

## Goal

Add shared queries for current-calendar-month points and lifetime XP under the household timezone (`Europe/Berlin`), and display each member's monthly points, lifetime XP, garden stage, and the current month label on the household home page.

## Acceptance criteria

- [ ] A shared score calculation module `household/scores.py` provides:
  - `MemberScore` dataclass containing `member`, `monthly_points`, `lifetime_xp`, and `garden_stage`,
  - `get_household_scores(at=None)` returning the month label (e.g. `September 2026`) and scores for all members in display order,
  - `get_member_scores(member, at=None)` returning a `MemberScore` for a single member.
- [ ] Monthly points sum awarded points for completions within the current local calendar month in `Europe/Berlin` (from 00:00:00 of the 1st of the month to 00:00:00 of the 1st of next month).
- [ ] Lifetime XP sums all awarded points ever earned by the member across all time, including points from deleted (inactive) chores.
- [ ] Members with zero completions correctly have 0 monthly points, 0 lifetime XP, and "Empty soil" garden stage.
- [ ] Correctly handles local month boundaries and year rollover (e.g. December to January).
- [ ] Scores naturally reflect the calendar month based on query calculation without background reset jobs or cached duplicate totals.
- [ ] The household home page (`/`) displays:
  - the current month label (e.g. `Household scores — September 2026`),
  - each member's name, monthly points, lifetime XP, and garden stage label, in member display order.
- [ ] Submitting a completion redirects to the household page with updated scores reflected immediately.

## Out of scope

- Rendering SVG garden visuals (handled in Task 15).
- Individual member pages (handled in Task 14).
- Neighborhood shared garden overview page (handled in Task 16).

## Constraints

- Files: `household/scores.py`, `household/views.py`, `household/templates/household/home.html`, `household/tests/test_scores.py`.
- Keep business logic in Python, outside templates.
- Ensure timezone calculations use `Europe/Berlin` calendar month boundaries.

## QA: PASS

- [x] `household/scores.py` provides `MemberScore`, `get_household_scores(at=None)`, and `get_member_scores(member, at=None)` — PASS
- [x] Monthly points correctly sum awarded points for completions within current local calendar month in `Europe/Berlin` — PASS
- [x] Lifetime XP sums all awarded points ever earned, including past months and inactive chores — PASS
- [x] Members with zero completions have 0 monthly points, 0 lifetime XP, and "Empty soil" — PASS
- [x] Correctly handles local month boundaries and year rollover (tested December -> January and CEST UTC offset) — PASS
- [x] No background reset jobs or duplicate persisted totals — PASS
- [x] Household home page displays month label, member scores (monthly points, lifetime XP, garden stage) in display order — PASS
- [x] Completing chore updates scores immediately on redirect — PASS

Tests: `.venv\Scripts\python.exe manage.py test`, 124 passed, 0 failed.

Status: CLOSED
