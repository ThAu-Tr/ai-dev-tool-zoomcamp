# GrabTab — MVP Scope

**Tagline:**  
**Grab it. Add it. Share it.**

## Product Idea

GrabTab is a shared household shopping and expense tool.

Its core idea is to connect a shared shopping list directly with expense splitting:

1. Someone adds an item the household needs.
2. Another member buys it.
3. They mark it as bought and enter the price.
4. The item is removed from the shopping list.
5. It automatically becomes a shared expense.
6. The expense is split equally between the relevant household members.

Members can also add expenses directly without using the shopping list.

## Core USP

**A shared shopping list that automatically turns purchases into split expenses.**

GrabTab combines two workflows that are usually separate:

- coordinating what the household needs
- tracking and splitting shared expenses

The goal is not to add unnecessary complexity, but to make the common household flow from **need → purchase → shared expense** seamless.

---

# MVP Scope

## 1. User Accounts

- Every household member has an individual account.
- Actions and expenses are tied to the logged-in user.

## 2. One Household

- For the MVP, each user belongs to exactly one household.
- Multiple households per user are out of scope.

## 3. Joining a Household

- A household member can invite others via an invite link or invite code.
- New members create an account and join the household through that invite.

## 4. Shared Shopping List

The household has one shared shopping list.

Members can:

- add simple item names
- see who added each item
- mark an item as bought

The MVP shopping list does **not** include:

- quantities
- categories
- brands
- notes
- recurring items

## 5. Buying an Item

When a shopping-list item is marked as bought:

- the buyer enters the price
- the item is removed from the active shopping list
- an expense is created automatically
- the buyer is stored as the person who paid

There is no separate “bought items” list required for the MVP.

## 6. Direct Expenses

Members can also create an expense directly without using the shopping list.

Example:

> Cleaning supplies — €12

The expense is associated with the user who created it.

## 7. Expense Splitting

Default behavior:

- an expense is split equally between all household members

Optional behavior:

- the creator can select only specific household members
- the expense is then split equally between those selected members

The MVP does **not** support:

- custom percentages
- custom individual amounts
- weighted splits

## 8. Editing and Deleting Expenses

- Users can edit expenses they created themselves.
- Users can delete expenses they created themselves.
- Users cannot edit or delete expenses created by another household member.

## 9. Balances

GrabTab shows both:

### Net Balance

Example:

- Anna: +€20
- Ben: -€4
- Clara: -€16

This shows each member's overall position within the household.

### Pairwise Debts

Example:

- Ben owes Anna €10
- Clara owes Anna €10
- Clara owes Ben €6

This shows exactly who owes whom.

## 10. Settling Debts

- Pairwise debts can be marked as settled.
- Settlement represents that the repayment happened outside GrabTab.
- GrabTab only records that the debt has been settled.

---

# Core Features

The MVP can be grouped into four main feature areas.

## Household & Member Management

- individual accounts
- one household per user
- invite link or invite code

## Shared Shopping List

- shared list of needed items
- any member can add items
- show who added each item
- bought items automatically become expenses

## Expense Tracking & Splitting

- create expenses directly
- create expenses automatically from shopping-list purchases
- equal split across all members by default
- optionally split only between selected members
- users can edit or delete only their own expenses

## Balances & Settlement

- net balance per member
- pairwise debts
- mark pairwise debts as settled

---

# Main User Flow

## Shopping List Flow

**Add need → Buy item → Enter price → Expense created → Cost split**

Example:

1. Anna adds `Toilet paper`.
2. Ben buys it.
3. Ben marks it as bought and enters `€4.50`.
4. `Toilet paper` disappears from the shopping list.
5. GrabTab creates a €4.50 expense paid by Ben.
6. The expense is split equally between the household members.

## Direct Expense Flow

**Add expense → Enter price → Choose participants → Cost split**

Example:

1. Clara adds `Cleaning supplies`.
2. She enters `€12`.
3. She chooses Anna and Clara as participants.
4. Each owes €6 of the expense.

---

# Explicitly Out of Scope for the MVP

These ideas may be useful later, but should not be part of the first version:

- multiple households per user
- custom split percentages
- custom split amounts
- weighted splits
- shopping-list quantities
- shopping-list categories
- brands or notes
- receipt scanning
- receipt item parsing
- purchase approvals
- price history
- recurring-item suggestions
- household staples prediction
- gamification
- contribution or fairness scores
- automatic suggestions for who should buy something
- ownership tracking for durable household goods
- spend forecasting
- advanced or partial settlement workflows
- any feature that requires users to change normal household behavior just to use the app

---

# Product Positioning

GrabTab should stay simple.

It is **not** intended to be:

- a full accounting system
- a budgeting platform
- a receipt-management tool
- a household-management suite

It is a lightweight household tool built around one simple idea:

> **The household shopping list and the household expense tracker should be the same workflow.**

## Name

**GrabTab**

The name reflects the product flow:

**Grab something → put it on the shared tab.**

## Tagline

**Grab it. Add it. Share it.**
