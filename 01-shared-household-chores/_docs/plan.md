# Shared Household Chores Tool — Minimal Version

## 1. Product Direction

This version is intentionally reduced to the smallest useful form while still keeping the core identity of the app.

The main product idea is:

> Manage chores → complete them → track contribution → grow your garden.

The app is designed for a shared household / WG with multiple equal members.

## 2. No Login

The app has **no authentication or login system**.

This means:

- The app does not automatically know who is currently using it.
- Household members are predefined in the app.
- When a chore is completed, the user selects which household member completed it.
- No account management, passwords, email verification, or authentication flows are required.

This keeps the first version much smaller and easier to build.

Importantly, **no login does not mean no individual views**.

The app can still have individual member pages or views. The difference is simply that the user manually selects whose view they want to see.

## 3. Household Structure

The first version contains:

- One shared household
- A small predefined list of members
- One shared chore system

There is no need to support multiple households in the first version.

## 4. The Four Core Features

### 4.1 Shared Chore Management

Members can manage the shared chore list.

Each chore contains:

- Chore name
- Frequency
- Point value
- Due status

The app shows whether chores are:

- Due
- Overdue
- Not yet due

If a chore becomes overdue, it stays overdue until someone completes it.

Members can:

- Add chores
- Edit chores
- Delete chores

Rooms or shared-space categories are not required for this minimal version.

### 4.2 Chore Completion & Points

Any household member can complete any available chore.

Because there is no login, the user selects the member who completed the chore.

The flow is:

1. Select household member
2. Select / open chore
3. Mark chore as done
4. Chore points are awarded automatically
5. Completion is recorded
6. The next due date is calculated

Each completion contributes to:

- Monthly points
- Lifetime XP

The app should also store basic completion history:

- Chore
- Member
- Completion date
- Points earned

### 4.3 Individual Member Views

Each household member has an individual view.

The user can manually open or select a member.

The member view shows:

- Member name
- Current monthly points
- Lifetime XP
- Completed chore history
- Personal garden

There is no account ownership or private view. All household members can view every member page.

The individual view exists only to organize information around one member.

### 4.4 Garden Progression

Each household member has a personal garden.

The garden grows automatically based on Lifetime XP.

For the minimal version:

- Garden progression is purely cosmetic
- Users cannot choose plants
- Users cannot decorate the garden
- There is no XP shop
- There is no inventory
- There are no customization options

Example progression:

1. Empty soil
2. Seed
3. Sprout
4. Small plant
5. Flowers
6. Bushes
7. Tree
8. Richer garden

The exact XP thresholds can be decided later.

## 5. Neighborhood View

In addition to individual member views, the app has one shared **Neighborhood View**.

This view shows all members' gardens together.

The purpose is to create a shared visual overview of long-term participation.

Example:

- Alex's garden
- Sam's garden
- Jamie's garden

All shown side by side in one shared neighborhood.

From the neighborhood, the user can optionally open an individual member view.

## 6. Monthly Points

Each household member has a monthly point total.

Points are earned by completing chores.

At the beginning of each new month:

- Monthly scores reset to zero
- Everyone gets a fresh start
- Lifetime XP remains unchanged
- Historical chore completions remain stored

The monthly score represents short-term contribution.

## 7. Lifetime XP

Lifetime XP represents long-term contribution.

For the minimal version:

> 1 chore point = 1 Lifetime XP

Lifetime XP never resets.

It is used to determine garden progression.

## 8. Core App Views

The minimal app can be built around only a few simple views.

### Shared Household / Chore View

Shows:

- Household members
- Shared chore list
- Due / overdue chores
- Point values
- Completion controls
- Current monthly scores

### Individual Member View

Shows:

- Monthly points
- Lifetime XP
- Completion history
- Personal garden

### Neighborhood View

Shows:

- All household members
- All gardens together

The app can still feel very small even with these individual views because there is no authentication or account system.

## 9. Explicitly Out of Scope

The following features are intentionally excluded from this minimal version:

- Login
- User accounts
- Authentication
- Multiple households
- Notifications
- Rooms / shared-space structure
- Achievements
- Ad-hoc chores
- Audit history
- Chore assignment
- Chore rotation
- Chore claiming
- Completion verification
- Voting
- Point approval workflows
- Garden customization
- XP shop
- Inventory
- Complex notification settings
- Household chat
- Comments
- Role-based permissions
- Admin users
- Automated fairness balancing
- Escalating overdue urgency

These can be considered later if the basic app works well.

## 10. Minimal Core Loop

The smallest meaningful user flow is:

1. Open the household view
2. See which chores are due
3. Select who completed a chore
4. Mark the chore as done
5. Award points automatically
6. Update monthly score
7. Update Lifetime XP
8. Grow the member's garden
9. View progress in the individual or neighborhood view

This is the smallest version that still preserves the distinctive identity of the product.
