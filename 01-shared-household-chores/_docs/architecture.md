# Shared Household Chores Tool — Architecture

Status: selected architecture for the minimal version.

Decision date: September 5, 2026.

Product requirements: [plan.md](plan.md).

## 1. Architecture decision

Build one server-rendered Django application backed by SQLite. Use Django templates and forms for the interface, with plain CSS and SVG or static images for the gardens.

The application supports one household with three predefined, equal members and no login. The members are Alex, Sam, and Jamie, displayed in that order. Users select the member who completed a chore. Member pages organize public household information; they do not represent authenticated accounts.

The core flow is:

> Manage chores → complete them → track contribution → grow your garden.

## 2. Selected technology stack

| Layer | Choice | Purpose |
| --- | --- | --- |
| Language | Python 3.14.7 | Application and business logic |
| Web framework | Django 6.1.1 | Routing, views, forms, validation, and HTML rendering |
| Database | SQLite bundled with the Python runtime, compatible with Django | Shared persistent household data |
| Database access | Django ORM and migrations | Models, queries, constraints, and schema changes |
| Frontend | Django templates and standard HTML forms | Household, member, and neighborhood pages |
| Styling | Plain CSS | Responsive layout and visual styling |
| Garden visuals | SVG or static images, optionally animated with CSS | Cosmetic stages derived from lifetime XP |
| Tests | Django's built-in testing tools | Business rules, database behavior, and form/view flows |

Python and Django versions are the selected baseline from the official release check on the decision date. Apply supported patch updates as the project develops. Django 6.1 supports Python 3.14. SQLite's upstream release at the time of the check was 3.53.4; this is not a requirement to separately install or replace Python's bundled SQLite library.

Django 5.2 LTS was considered for its longer support window, but Django 6.1.1 was selected for this new project. Django 6.1 receives extended support through December 2027; plan a supported framework upgrade before then.

HTMX is an optional future enhancement, not an initial dependency. No frontend build pipeline or separate API service is required.

## 3. Application structure

Use one Django project for configuration and one Django application for household features. Keep related functionality together while the product remains small.

- Models define members, chores, and completions.
- Forms validate chore changes and member selection.
- Views handle requests and render pages or redirect after successful submissions.
- A small shared business-logic module handles completion, recurrence, and garden-stage calculations.
- Templates share a base layout and reusable garden and score displays.
- Static files contain CSS and garden artwork.

The browser sends requests to Django; Django reads and writes SQLite and returns HTML. Database credentials or direct database access are never needed in the browser.

## 4. Core pages and interactions

| Page | Contents and actions |
| --- | --- |
| Household | Active chores, due status, point values, member selection, completion controls, monthly scores, and links to add/edit/delete chores |
| Member | Name, current monthly points, lifetime XP, completion history, and personal garden |
| Neighborhood | All members' gardens together, with links to member pages |
| Chore forms | Add/edit forms and deletion confirmation |

Initially, use normal form submissions and full page loads. A successful write follows the POST/Redirect/GET pattern: submit the form, save the change, then redirect to an updated page. Invalid forms show validation errors without saving changes.

All mutations use POST and Django's CSRF protection. Member selection supplies attribution only. There are no private member views, roles, or Django admin interface in the product.

If partial updates later improve the experience, add HTMX to selected interactions. Django's built-in template partials, available since Django 6.0, can support these responses without a separate template-partials dependency.

## 5. Data model

Use three main models. A separate Household model is unnecessary for the single-household scope.

| Model | Main stored information | Relationships |
| --- | --- | --- |
| Member | Identifier, display name, optional display order | One member has many completions |
| Chore | Identifier, name, frequency, point value, next due date, active/deleted state, completion version | One chore has many completions |
| Completion | Identifier, member, chore, completion timestamp, points earned, chore-name snapshot, completed version | Belongs to one member and one chore |

Predefine Alex, Sam, and Jamie in that display order through a repeatable setup mechanism, such as a data migration or fixture. Member management is outside the initial UI.

Store awarded points on each completion. Editing a chore's point value must not change previous awards. A chore-name snapshot preserves readable historical records after renaming.

Implement user-facing chore deletion by marking the chore inactive and removing it from active lists. Keep its completion records and their contribution to monthly points and lifetime XP. This preserves history without introducing an audit-history feature.

Do not persist duplicate score totals or garden state initially; derive them from completions.

## 6. Completing a chore

1. Validate the selected member, active chore, and submitted completion version.
2. Check whether the chore is eligible for completion under the chosen due-date policy.
3. In one database transaction, conditionally advance the chore's completion version and due date and create its completion record with the awarded points.
4. Commit both changes together, or roll back both if any part fails.
5. Redirect to the household page, where scores and garden stages are recalculated.

Protect against double clicks, retries, and two members submitting the same occurrence. A conditional update against the expected completion version, together with a unique constraint on chore and completed version, can ensure only one submission awards points for that occurrence. POST/Redirect/GET alone is not duplicate protection.

Keep transactions short and use concurrency handling that works with SQLite; do not rely on row-locking behavior that SQLite does not provide.

## 7. Dates, points, and progression

### Due status and recurrence

Use `Europe/Berlin` as the household timezone for local due dates, displayed completion dates, and calendar-month boundaries. Store a next due date and derive status using the household's local date:

- Before the due date: not yet due.
- On the due date: due.
- After the due date: overdue.

Overdue chores remain overdue until completed. No scheduled process advances an unfinished chore.

Represent frequency as a whole-number interval in days from 1 through 365 inclusive. Frequency is required. Reject blank, zero, negative, fractional, unsupported, and out-of-range values.

Anchor recurrence to the previous scheduled due date, not the completion date. After a successful completion, add whole frequency intervals to the stored due date until the resulting next due date is strictly after the local completion date. This rule keeps a chore on its schedule while ensuring that completion after multiple missed intervals never leaves it immediately due or overdue.

Reject attempts to complete a chore before its local due date. A rejected early attempt creates no completion, awards no points or lifetime XP, and changes neither the due date nor completion version.

For a new chore, let the user choose the initial due date. Default it to the current `Europe/Berlin` date and permit past dates.

Editing a chore's frequency leaves its stored due date unchanged whether that date is future, due, or overdue. The new frequency applies when calculating the next due date after the next successful completion. Direct due-date editing is allowed. Name-only and point-only edits leave the due date unchanged. All edits preserve completion history and previously awarded points.

### Chore values and names

Points are required whole numbers from 1 through 100 inclusive. Reject blank, zero, negative, fractional, and out-of-range values.

A chore name is required; reject a blank name, including one that is empty after normalization. Trim leading and trailing whitespace, collapse internal whitespace to single spaces, and apply the 100-character maximum after normalization. Reject case-insensitive duplicate names among active chores. An inactive chore does not prevent reuse of its name.

### Scheduling examples

- On-time completion and year rollover: a 7-day chore due on December 31, 2026 and completed that day becomes due on January 7, 2027.
- Completion after multiple missed intervals: a 7-day chore due on January 1, 2026 and completed on January 20 advances through January 8 and January 15, then becomes due on January 22, 2026.
- Early completion: an attempt on January 9, 2026 for a chore due on January 10 is rejected. It creates no completion or award and changes neither the completion version nor due date.
- Future-due frequency edit: on March 10, 2026, changing a 7-day chore due March 20 to 14 days leaves the due date at March 20. If completed on March 20, it next becomes due April 3, using the new 14-day interval.
- Overdue frequency edit: on March 20, 2026, changing a 7-day chore still due March 1 to 14 days leaves the overdue due date at March 1. Completion on March 20 advances from March 1 through March 15 to a next due date of March 29, using the new 14-day interval.

### Monthly points

Sum awarded points from completions within the current calendar month in the configured household timezone. Use the start of the month as an inclusive boundary and the start of the next month as an exclusive boundary.

At a new month, the query naturally returns the new month's total. There is no reset job and no deletion of history.

For example, in `Europe/Berlin`, a completion at January 31, 2026 23:30 counts toward January, while one at February 1, 2026 00:30 counts toward February. Each month begins inclusively at local midnight on its first day and ends exclusively at the next month's start.

### Lifetime XP

Sum all awarded completion points for the member. One chore point equals one lifetime XP. This total never resets.

### Garden progression

Map lifetime XP to a fixed sequence of garden stages. Store thresholds in one shared definition and use the same calculation on member and neighborhood pages.

The progression uses these inclusive minimum lifetime-XP thresholds:

| Minimum lifetime XP | Identifier | Readable label |
| ---: | --- | --- |
| 0 | `empty_soil` | Empty soil |
| 25 | `seed` | Seed |
| 75 | `sprout` | Sprout |
| 150 | `small_plant` | Small plant |
| 300 | `flowers` | Flowers |
| 500 | `bushes` | Bushes |
| 800 | `tree` | Tree |
| 1200 | `richer_garden` | Richer garden |

The member's stage is the stage with the greatest threshold less than or equal to their lifetime XP. The ordered stage definition in `household/garden.py` is the single application source of truth for thresholds, identifiers, and labels.

Garden artwork will use lightweight static SVG files built from one reusable plot scene, with simple additions for each successive stage. Raster artwork, animation, and external illustration libraries are not required. Creating the artwork remains a separate task. There is no separate Garden model, inventory, shop, or customization system.

Store completion timestamps as timezone-aware timestamps and convert them to `Europe/Berlin` for displayed dates, month boundaries, and due-date calculations.

## 8. Development and deployment

Use an isolated Python environment and pinned application dependencies. Django's development server is sufficient for local development.

Deploy one application instance using a production WSGI server, with SQLite on persistent local storage. Select the hosting provider, production server, and static-file serving configuration when deployment is planned. The development server is not the production server.

Back up the database with a SQLite-aware backup method and keep the database outside replaceable application-release files. Uploaded media storage is unnecessary for predefined garden assets.

SQLite is appropriate for the expected small household workload. Reconsider PostgreSQL if hosting requires multiple application instances or concurrent writes become a practical limitation.

The app intentionally has no authentication: anyone who can access it can use its household actions. Choose deployment visibility accordingly; selecting a member does not verify identity.

## 9. Validation priorities

Use focused tests for the behavior that protects household data:

- Completion records, awarded points, and due-date changes succeed or fail together.
- Duplicate or stale completion submissions do not award points twice.
- Monthly totals respect timezone and month boundaries; lifetime XP remains intact.
- Chore edits and deletion preserve earned points and readable history.
- Due and overdue states and recurrence follow the chosen rules.
- Garden stages change at the configured XP thresholds.
- Forms reject invalid input and the core pages display the expected member data.

## 10. Deliberate simplifications

- One project, one Django application, and one database.
- Django ORM, migrations, forms, and testing tools cover the initial needs.
- Standard HTML submissions keep browser behavior straightforward.
- Scores, due status, and gardens are calculated from stored facts.
- No background workers, scheduled reset tasks, caches, or real-time synchronization are required initially.
- The feature exclusions in [plan.md](plan.md) remain authoritative.

## 11. Decision status

The owner approved the household, scheduling, chore-validation, and garden-progression rules in section 7 on 2026-09-06. The lightweight static-SVG direction is also selected. No choices within those decisions' scope remain open.

The following decisions remain outside that scope:

- Hosting, production serving, and backup arrangements.

## 12. Official references

Versions and compatibility were checked during the stack selection on September 5, 2026.

- [Python releases](https://www.python.org/downloads/)
- [Django releases and support periods](https://www.djangoproject.com/download/)
- [Django Python compatibility and SQLite setup](https://docs.djangoproject.com/en/6.1/faq/install/)
- [Django forms](https://docs.djangoproject.com/en/6.1/topics/forms/)
- [Django database backend notes](https://docs.djangoproject.com/en/6.1/ref/databases/)
- [Django template partials introduced in 6.0](https://docs.djangoproject.com/en/6.1/releases/6.0/#template-partials)
- [SQLite downloads](https://www.sqlite.org/download.html)
