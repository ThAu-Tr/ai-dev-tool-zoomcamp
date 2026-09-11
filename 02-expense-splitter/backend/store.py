"""Replaceable in-memory persistence adapter for the GrabTab API."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4


class DomainError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


SEED_STATE = {
    "household": {
        "id": "elm-street-home",
        "name": "Elm Street Home",
        "inviteCode": "ELM-782",
        "inviteLink": "https://grabtab.app/join/elm-782",
    },
    "members": [
        {"id": "anna", "name": "Anna", "color": "anna"},
        {"id": "ben", "name": "Ben", "color": "ben"},
        {"id": "clara", "name": "Clara", "color": "clara"},
    ],
    "shopping": [
        {"id": "s1", "name": "Oat milk", "addedBy": "clara"},
        {"id": "s2", "name": "Toilet paper", "addedBy": "anna"},
        {"id": "s3", "name": "Dishwasher tabs", "addedBy": "ben"},
    ],
    "expenses": [
        {"id": "e1", "name": "Internet", "amount": 42.0, "paidBy": "anna", "participants": ["anna", "ben", "clara"], "createdAt": "2026-09-05", "source": "direct"},
        {"id": "e2", "name": "Fresh produce", "amount": 28.4, "paidBy": "ben", "participants": ["anna", "ben", "clara"], "createdAt": "2026-09-08", "source": "shopping"},
        {"id": "e3", "name": "Cleaning supplies", "amount": 12.0, "paidBy": "clara", "participants": ["anna", "clara"], "createdAt": "2026-09-09", "source": "direct"},
    ],
    "settlements": [],
}


class MockDatabase:
    """Stateful test/development store with the same surface a real repo needs."""

    def __init__(self) -> None:
        self._state = deepcopy(SEED_STATE)

    def reset(self) -> None:
        self._state = deepcopy(SEED_STATE)

    def is_member(self, user_id: str) -> bool:
        return any(member["id"] == user_id for member in self._state["members"])

    def household_state(self, current_user_id: str) -> dict:
        state = deepcopy(self._state)
        state["household"].pop("id")
        state["currentUserId"] = current_user_id
        return state

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"

    @staticmethod
    def _validated_name(name: str) -> str:
        clean_name = name.strip()
        if not clean_name or len(clean_name) > 60:
            raise DomainError(400, "Name must contain between 1 and 60 characters")
        return clean_name

    def _validated_participants(self, participant_ids: list[str]) -> list[str]:
        if not participant_ids:
            raise DomainError(400, "Choose at least one participant")
        if len(set(participant_ids)) != len(participant_ids):
            raise DomainError(400, "Participants must be unique")
        member_ids = {member["id"] for member in self._state["members"]}
        if not set(participant_ids).issubset(member_ids):
            raise DomainError(400, "All participants must belong to your household")
        return participant_ids

    @staticmethod
    def _amount(value: float) -> float:
        amount = Decimal(str(value))
        if amount <= 0:
            raise DomainError(400, "Amount must be greater than zero")
        return float(amount.quantize(Decimal("0.01")))

    def add_shopping_item(self, user_id: str, name: str) -> None:
        self._state["shopping"].insert(0, {"id": self._new_id("s"), "name": self._validated_name(name), "addedBy": user_id})

    def purchase_item(self, user_id: str, item_id: str, amount: float) -> None:
        item = next((item for item in self._state["shopping"] if item["id"] == item_id), None)
        if item is None:
            raise DomainError(404, "Shopping item not found")
        self._state["shopping"].remove(item)
        self._state["expenses"].insert(0, {
            "id": self._new_id("e"), "name": item["name"], "amount": self._amount(amount),
            "paidBy": user_id, "participants": [member["id"] for member in self._state["members"]],
            "createdAt": date.today().isoformat(), "source": "shopping",
        })

    def create_expense(self, user_id: str, name: str, amount: float, participant_ids: list[str]) -> None:
        self._state["expenses"].insert(0, {
            "id": self._new_id("e"), "name": self._validated_name(name), "amount": self._amount(amount),
            "paidBy": user_id, "participants": self._validated_participants(participant_ids),
            "createdAt": date.today().isoformat(), "source": "direct",
        })

    def _owned_expense(self, user_id: str, expense_id: str) -> dict:
        expense = next((expense for expense in self._state["expenses"] if expense["id"] == expense_id), None)
        if expense is None:
            raise DomainError(404, "Expense not found")
        if expense["paidBy"] != user_id:
            raise DomainError(403, "You can only edit your own expenses")
        return expense

    def update_expense(self, user_id: str, expense_id: str, name: str, amount: float, participant_ids: list[str]) -> None:
        expense = self._owned_expense(user_id, expense_id)
        expense.update({"name": self._validated_name(name), "amount": self._amount(amount), "participants": self._validated_participants(participant_ids)})

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        expense = self._owned_expense(user_id, expense_id)
        self._state["expenses"].remove(expense)

    def _outstanding_debts(self) -> set[tuple[str, str]]:
        balances = {member["id"]: Decimal("0") for member in self._state["members"]}
        for expense in self._state["expenses"]:
            amount = Decimal(str(expense["amount"]))
            balances[expense["paidBy"]] += amount
            share = amount / len(expense["participants"])
            for participant in expense["participants"]:
                balances[participant] -= share
        debtors = [[member_id, -balance] for member_id, balance in balances.items() if balance < 0]
        creditors = [[member_id, balance] for member_id, balance in balances.items() if balance > 0]
        debts: set[tuple[str, str]] = set()
        while debtors and creditors:
            debtor, creditor = debtors[0], creditors[0]
            debts.add((debtor[0], creditor[0]))
            amount = min(debtor[1], creditor[1])
            debtor[1] -= amount
            creditor[1] -= amount
            if debtor[1] == 0:
                debtors.pop(0)
            if creditor[1] == 0:
                creditors.pop(0)
        settled = {(settlement["from"], settlement["to"]) for settlement in self._state["settlements"]}
        return debts - settled

    def settle_debt(self, user_id: str, from_member_id: str, to_member_id: str) -> None:
        if not self.is_member(from_member_id) or not self.is_member(to_member_id) or from_member_id == to_member_id:
            raise DomainError(400, "Settlement members must be different household members")
        if (from_member_id, to_member_id) not in self._outstanding_debts():
            raise DomainError(400, "There is no outstanding debt for these members")
        self._state["settlements"].insert(0, {
            "id": self._new_id("st"), "from": from_member_id, "to": to_member_id,
            "createdAt": datetime.now(UTC).isoformat(), "createdBy": user_id,
        })
