# Implementation backlog

This backlog implements [plan.md](plan.md) using [architecture.md](architecture.md): Python 3.14.7, Django 6.1.1, bundled SQLite, Django templates/forms, and plain CSS/SVG. The product serves one household with predefined members and no authentication; HTMX and a separate API are outside the initial implementation.

Tasks are ordered for implementation, and each description states the existing components it needs. A session means roughly two to four focused hours, including verification, with prerequisite components and required owner decisions available. Each task can be handed over on its own; this does not mean it can run before its prerequisites exist, and larger defects discovered during verification should become separate follow-up tasks.

## 1. Set up an empty Django project with a passing test

Goal: Establish a runnable project and a working test command before adding product features.

Description: Create an isolated Python environment, pinned dependencies, one Django project, and one empty household application using Python 3.14.7, Django 6.1.1, and SQLite. Add a minimal placeholder page and a Django smoke test that verifies its successful response, without adding domain models or authentication flows. Document installation, development-server, and test commands in README.md, exclude local environments and database files from version control, and verify the test passes.

## 2. Resolve household and scheduling rules

Goal: Record the product decisions needed to implement members, dates, and chore validation.

Description: Using the open decisions in _docs/architecture.md, agree with the owner on member names/order, household timezone, allowed frequencies and point values, recurrence behavior, early completion, initial due dates, and the effect of frequency edits on an existing due date. Record the decisions in the architecture document with concrete examples for an overdue completion and a frequency edit. This is a documentation task and requires no application features.

## 3. Define garden progression and implement stage calculation

Goal: Establish and test one shared mapping from lifetime XP to cosmetic garden stages.

Description: Using the empty Django project, agree with the owner on the cosmetic garden's stage sequence, increasing XP thresholds, and simple SVG or static-image direction, and record them in _docs/architecture.md. Implement a deterministic calculation returning a stage identifier and readable label from XP, without a Garden model or dependencies on chore implementation. Test zero XP, values immediately below and at every threshold, and values above the final threshold; artwork creation is a separate task.

## 4. Add member and chore storage

Goal: Persist predefined household members and recurring chores.

Description: Using the empty Django project and documented member/scheduling decisions, add Member fields for display name/order and Chore fields for name, frequency, points, next due date, active state, and completion version, with migrations and appropriate constraints. Provide and document repeatable predefined-member setup without accounts or an admin interface. Verify fresh migrations, repeated setup without duplicates or overwritten data, and rejection of invalid chore values.

## 5. Add completion history storage

Goal: Preserve each member's earned points and the historical chore name.

Description: Using the Member and Chore models, add a Completion model and migration containing member, chore, timezone-aware completion timestamp, awarded points, chore-name snapshot, and completed version. Enforce uniqueness for a chore and completed version, and prevent relationship deletion from silently removing earned history. Test duplicate rejection and verify that later changes to a chore's name or point value do not alter stored completion snapshots.

## 6. Implement due status and recurrence calculations

Goal: Calculate when a chore is due and its next due date consistently.

Description: Using the Chore model and documented scheduling decisions, implement shared calculations for not-yet-due, due, overdue, completion eligibility, and the next due date. Use the configured household timezone and leave overdue chores unchanged until completion. Test date boundaries, overdue completion, early-completion policy, and the agreed behavior around month/year changes.

## 7. Build the shared layout and household chore list

Goal: Provide a responsive household page showing active chores and their due status.

Description: Using Member and Chore models and due-status calculations, create a shared Django base template and household page showing members and active chores with names, frequencies, points, and textual status labels. Add plain responsive CSS, visible keyboard focus, space for messages, an empty state, and predictable chore ordering; add navigation as destination pages become available. Test inactive-chore exclusion and the three due states, and visually check narrow and wide layouts without building a design system.

## 8. Add chore creation and editing forms

Goal: Let household users create and edit recurring chores through shared form behavior.

Description: Using Chore and Completion models, the household layout, and recorded scheduling decisions, build a shared Django form with create/edit views for name, frequency, points, and the agreed due-date behavior. Use CSRF-protected POST, display invalid input without saving, redirect after success, and handle missing or inactive chores clearly. Test creation, invalid values, frequency edits, GET requests without mutations, and preservation of previously awarded points and chore-name snapshots.

## 9. Add chore deletion with history preservation

Goal: Remove chores from active use without losing completion history.

Description: Using the Chore and Completion models and household page, add a deletion confirmation page whose POST action marks the chore inactive. Keep all completion records intact, redirect after success, and ensure visiting the confirmation page alone changes nothing. Test that the chore disappears from the active list, repeated deletion is handled clearly, and historical contributions remain available.

## 10. Implement atomic chore completion

Goal: Record a completion and advance its chore in one transaction with version protection.

Description: Using the Member, Chore, and Completion models and recurrence calculations, implement a shared completion operation that validates the member, active chore, eligibility, and expected completion version. Use a short SQLite-compatible transaction with a conditional version update and occurrence uniqueness constraint so snapshots and the next due date commit together, exposing clear outcomes for success and stale or invalid requests. Test successful completion, rollback on failure, and sequential stale/repeated submissions; concurrent database contention is verified in the following dedicated task before the operation is exposed through the UI.

## 11. Verify competing completions and handle SQLite contention

Goal: Ensure simultaneous completion attempts cannot award points twice or leave partial changes.

Description: Using the existing version-guarded completion operation, create a focused concurrency test with separate database connections against a temporary file-backed SQLite database. Exercise competing submissions for the same chore occurrence and define bounded lock-contention handling that returns a recoverable outcome without hiding unrelated database errors. Verify exactly one award when an attempt succeeds, no partial state after failed attempts, and safe subsequent retries; document the operation's outcomes for its UI caller.

## 12. Add member selection and completion controls

Goal: Let a user attribute and submit a chore completion from the household page.

Description: Using the household page and atomic completion operation, add a clearly labeled member selector and completion form carrying the expected chore version. Submit through CSRF-protected POST and redirect with a success or understandable stale/invalid-submission message, preserving the rule that member selection is attribution rather than login. Test the complete request flow, missing/invalid members, ineligible or inactive chores, and resubmission without duplicate points.

## 13. Calculate contributions and display household scores

Goal: Derive member contributions and show current monthly totals on the household page.

Description: Using Member and Completion records, the configured household timezone, and the household page, add shared queries for current-calendar-month points and lifetime XP, including inactive chores and members with zero completions. Display every member's monthly total and the month label on the household page, without persisting duplicate totals or adding reset jobs. Test local month boundaries, year rollover, unchanged lifetime XP/history across months, and updated scores after a completion redirect.

## 14. Build individual member pages

Goal: Provide a public household view of one member's contribution and history.

Description: Using Member and Completion records, contribution queries, and the shared layout, add a page showing the member name, monthly points, lifetime XP, and newest-first completion history with stored chore names, local completion dates, and awarded points. Link to these pages from the household view, provide an empty-history state, and return a clear not-found response for an unknown member. Test member-specific history and totals, including history for inactive chores; garden rendering is added separately.

## 15. Create reusable garden visuals

Goal: Render each agreed garden stage with lightweight, accessible artwork.

Description: Using the recorded garden-stage specification and shared layout, create minimal static SVG or image assets and one reusable Django template that accepts a stage and member name. Reuse a common scene with simple additions for later stages, supply a readable label and responsive sizing, and defer animation and elaborate illustration polish. Visually check every agreed stage at narrow and wide sizes so the deliverable remains a complete, simple asset set that fits one session.

## 16. Integrate personal gardens and the neighborhood page

Goal: Display consistent lifetime-XP gardens on member pages and a shared neighborhood page.

Description: Using existing member pages, lifetime-XP queries, stage calculation, and finished reusable garden visuals, render a personal garden on each member page and all named gardens on a responsive neighborhood page. Add links from neighborhood gardens to member pages and shared household/neighborhood navigation without creating new artwork. Test inclusion of zero-XP members, consistent stages across pages, a completion crossing a threshold, and unchanged gardens at a new month.

## 17. Test the complete household data journey

Goal: Verify the core product loop through a focused automated integration test.

Description: Using the completed chore, score, member, and neighborhood features, add a Django integration test for creating a chore, completing it for a selected member, and observing consistent history, points, and garden progression across responses. Exercise subsequent editing and deletion to verify earned contributions remain intact, reusing focused tests rather than duplicating every case. Run the relevant suite and record any substantial defects as separate follow-up tasks instead of expanding this session into a general repair effort.

## 18. Review browser usability and accessibility

Goal: Verify the finished pages can be used on narrow screens and with a keyboard.

Description: Using the completed household, form, member, and neighborhood pages, perform a browser walkthrough of navigation, member selection, completion, editing, deletion, and validation messages. Check keyboard focus, labels, textual status indicators, empty states, and garden layouts at narrow and wide sizes. Fix small presentation defects within the session and record larger findings as explicit follow-up tasks, with a short checklist of what was verified.

## 19. Document the production deployment choice

Goal: Select a concrete hosting arrangement for one Django instance and persistent SQLite storage.

Description: Using _docs/architecture.md and the owner's hosting constraints, select a provider, production WSGI server, static-file serving approach, persistent database location, and intended access visibility. Record required configuration and a deployment procedure, making clear that anyone who can reach this no-login app can use its household actions. This task produces a deployment decision and instructions without provisioning services or publishing the app.

## 20. Prepare production configuration

Goal: Make the application runnable under the documented production setup.

Description: Using the selected deployment procedure, add production configuration for secrets, debug mode, allowed hosts, the persistent SQLite path, static assets, and the chosen WSGI server. Document required environment values and startup/migration commands without committing secrets or using Django's development server for production. Verify production configuration and static-file serving in a local or isolated environment and run Django's deployment checks, documenting any hosting-dependent checks.

## 21. Add and verify database backup and restore

Goal: Make household records recoverable without risking the live database.

Description: Using the selected persistent SQLite deployment arrangement, provide a SQLite-aware backup procedure and a documented restore process with agreed backup storage and retention. Restore a backup into a separate temporary database and verify member records, chore state, and completion totals survive. Document how to stop writes during a real restore and ensure the verification never overwrites active household data.

## 22. Finalize the project handover documentation

Goal: Let a new contributor run, test, and operate the finished app from repository instructions.

Description: Using the implemented application and deployment/backup procedures, update README.md with prerequisites, environment setup, migrations, predefined-member initialization, development startup, tests, and links to operational instructions. Describe the three main pages and the no-login attribution model, and reconcile _docs/architecture.md with the final decisions. Verify the setup instructions against a fresh local database and record any remaining limitations without adding new product scope.
