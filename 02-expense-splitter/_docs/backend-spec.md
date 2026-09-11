# GrabTab backend specification

This is the implementation specification for the backend consumed by the
current frontend. `openapi.yaml` is the machine-readable request/response
contract; this document defines the persistence, authorization, and business
rules behind it.

## Scope and assumptions

- A user has one account and belongs to exactly one household.
- A household contains one shared active shopping list.
- All money is EUR for the MVP. Store monetary values as integer euro cents;
  never use floating-point values for calculation or storage.
- An expense is always an equal split. Custom ratios and partial payments are
  not MVP features.
- The current frontend identifies the person who paid an expense as both its
  `paidBy` user and its creator/owner.
- Each authenticated request is confined to the caller's household. IDs from
  another household must appear as `404`, rather than exposing their existence.

## Auth and household membership

Use `Authorization: Bearer <access-token>` for every endpoint currently used
by the UI. The API must derive `currentUserId` and `householdId` from the
validated token; clients must never submit either value to establish ownership.

The API needs user registration/login and invite-join endpoints before the
product can support the account and invitation flows in the product spec. They
are not required by the existing frontend because it has no login or join UI.
When implemented, registration must create a user, and a successful invite
join must add that user to exactly one household.

## Data model

Use immutable primary keys (UUIDs are recommended) and `created_at` / `updated_at`
timestamps on persisted records.

| Entity | Required fields | Rules |
| --- | --- | --- |
| `users` | `id`, `display_name`, auth credentials | One user may have one active household membership in the MVP. |
| `households` | `id`, `name`, `invite_code`, `invite_token` | Invite code/token must be unique and revocable. |
| `household_members` | `household_id`, `user_id`, `joined_at` | Unique on both columns; membership authorizes all shared resources. |
| `shopping_items` | `id`, `household_id`, `name`, `added_by_user_id`, `created_at`, `purchased_at` nullable | Only rows without `purchased_at` are active. The MVP does not need quantities, notes, categories, or brands. |
| `expenses` | `id`, `household_id`, `name`, `amount_cents`, `paid_by_user_id`, `source`, `created_at` | `source` is `direct` or `shopping`. The payer is also the only editor/deleter. |
| `expense_participants` | `expense_id`, `user_id` | At least one row per expense; users must belong to the expense household. |
| `debt_settlements` | `id`, `household_id`, `from_user_id`, `to_user_id`, `created_by_user_id`, `settled_at` | Records that payment occurred outside the app. See settlement rules below. |

`source_shopping_item_id` may be added to `expenses` as a nullable unique
foreign key. It gives auditability and guarantees one purchase cannot create
two expenses, without exposing a bought-items list to the MVP UI.

## API behavior

Follow [`openapi.yaml`](../openapi.yaml) exactly for endpoint paths, request
and response fields, status codes, and Bearer authentication.

The frontend is deliberately built around a `HouseholdState` snapshot. After
every successful mutation it replaces its in-memory state with the response.
Therefore every listed mutation must return a complete, internally consistent
`HouseholdState` object, ordered as follows:

- `shopping`: newest active items first.
- `expenses`: newest expenses first.
- `members`: a stable order is sufficient.
- `settlements`: chronological order is sufficient.

Map storage to the existing response fields as follows:

| API field | Backend source |
| --- | --- |
| `currentUserId` | Token subject/user ID |
| `household.name`, `inviteCode`, `inviteLink` | Household record; `inviteLink` is an absolute URL |
| `members[].id`, `members[].name` | Household membership and user record |
| `members[].color` | Presentation token. It may be deterministic from user ID or persisted; it has no authorization meaning. |
| `shopping[].addedBy` | `added_by_user_id` |
| `expenses[].paidBy` | `paid_by_user_id` |
| `expenses[].participants` | participant user IDs |
| `expenses[].createdAt` | `created_at` represented as ISO date for current UI compatibility |
| `settlements[].from`, `settlements[].to` | Settlement debtor and creditor IDs |

### Add shopping item

Trim the name. Reject an empty value or a value longer than 60 characters.
Set `added_by_user_id` to the authenticated user, not a client-provided ID.
Any household member may add an item.

### Purchase shopping item

`POST /v1/shopping-items/{itemId}/purchase` must be one database transaction:

1. Lock and verify that the active shopping item belongs to the caller's household.
2. Validate a positive amount, then convert it to cents exactly.
3. Mark the item purchased/remove it from active-list queries.
4. Create an expense with the item name, `source: shopping`, and payer equal to
   the authenticated user.
5. Add all *current* household members as equal participants.
6. Commit and return the new state.

The unique `source_shopping_item_id` constraint or equivalent lock is required
to prevent a double-click/retried request from creating two expenses.

### Direct expenses

Trim and validate `name` (1–60 characters) and require a positive amount.
Require a nonempty, unique `participantIds` list and verify every ID is a
current member of the caller's household. Set the payer to the authenticated
user; do not accept a payer field in the request. The payer does not need to
be a selected participant—the frontend allows this and the backend must retain
that behavior.

### Update and delete expenses

Only `paid_by_user_id == authenticated_user_id` authorizes either operation.
Return `403` if the expense exists in the caller's household but belongs to a
different member. Validate updates by the same rules as direct creation.

Deleting an expense must remove its participant rows. It must also cause
balances and outstanding debts to be recomputed. A soft-delete is acceptable
for auditability if it is excluded from normal state and balance queries.

### Balances and pairwise debts

The current UI derives balances locally from all expenses:

```text
net[expense.payer] += expense.amount
for each participant: net[participant] -= expense.amount / participant_count
```

A positive net balance means the member is owed money; a negative balance means
they owe. Pairwise debts are then produced by matching debtors to creditors in
the returned member order. This matching is deterministic only when the member
order is deterministic.

The MVP API currently returns source data rather than computed balance fields,
so the backend must preserve enough data for this calculation. Prefer also
implementing a backend balance service using integer cents and the same stable
member ordering. It can later be exposed as a dedicated balances endpoint
without breaking the snapshot endpoint.

For uneven-cent splits, allocate remainder cents deterministically (for example,
in ascending participant ID order) so the shares add exactly to the expense
total. The frontend currently uses floating-point division, so changing it to
consume backend-computed balances is recommended before supporting fractional-cent
edge cases in production.

### Settlements

The existing UI sends only `fromMemberId` and `toMemberId`, then hides the
matching calculated pairwise row. It does **not** send an amount and does not
reduce its displayed net balances. That is a compatibility constraint, but it
is not a sound long-term ledger model.

For the current UI contract, accept a settlement only when both members belong
to the caller's household and there is an outstanding deterministic debt from
`from` to `to`. Store a settlement record and return it in the snapshot. The
frontend uses that exact pair to hide the debt row.

Before a production backend is released, resolve this product/API gap with one
of these choices:

1. Treat settlement as a full settlement of the current pairwise debt and
   return server-computed balances and debts that include it; or
2. Add `amountCents` to the settlement request and model settlements as ledger
   transfers, supporting an accurate audit trail.

Option 1 matches the current button label and MVP scope best. Do not silently
delete the original expense when a debt is settled.

## Validation, errors, and consistency

- Use `400` for malformed JSON, blank names, invalid money, empty participants,
  duplicate participants, and members outside the household.
- Use `401` for absent/invalid/expired tokens.
- Use `403` only for a known in-household expense owned by another member.
- Use `404` for missing resources or resources in a different household.
- Return `{ "message": "human-readable explanation" }` for all error responses,
  matching the frontend's toast behavior.
- Mutation endpoints should support an `Idempotency-Key` header in the backend
  even though the current frontend does not send one. It is especially important
  for purchase and settlement requests.
- Use transactions for purchase, expense mutation, and settlement creation.

## Non-functional requirements

- Enforce household scoping in the data-access layer, not only in route code.
- Never return credentials, tokens, or resources from another household.
- Configure CORS only for the deployed frontend origin(s) and local development.
- Log request IDs and actor/household/resource IDs, but do not log Bearer tokens.
- Store UTC timestamps; serialize dates/times as ISO 8601.
- Unit-test authorization, participant validation, purchase idempotency, and
  balance rounding. Add integration tests for the shopping-to-expense transaction.

## Explicitly deferred

The current frontend has no UI or API contract for registration, login, invite
creation/acceptance, member removal, currencies, receipt uploads, custom splits,
partial settlements, or purchase history. Do not implement these as hidden MVP
behavior; add a versioned API and frontend flow when they enter scope.
