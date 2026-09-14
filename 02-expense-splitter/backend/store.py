"""Database-agnostic SQLAlchemy repository for GrabTab."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool


DEFAULT_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./grabtab.db")


class DomainError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class Base(DeclarativeBase):
    pass


class Household(Base):
    __tablename__ = "households"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    invite_code: Mapped[str] = mapped_column(String(32), unique=True)
    invite_link: Mapped[str] = mapped_column(String(512))


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(32))


class HouseholdMember(Base):
    __tablename__ = "household_members"

    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    added_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    amount_cents: Mapped[int] = mapped_column(Integer)
    paid_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(16))
    expense_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    source_shopping_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("shopping_items.id"), nullable=True, unique=True
    )
    participants: Mapped[list[ExpenseParticipant]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="ExpenseParticipant.user_id"
    )


class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"

    expense_id: Mapped[str] = mapped_column(ForeignKey("expenses.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    expense: Mapped[Expense] = relationship(back_populates="participants")


class DebtSettlement(Base):
    __tablename__ = "debt_settlements"
    __table_args__ = (UniqueConstraint("household_id", "from_user_id", "to_user_id", name="uq_settlement_pair"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    from_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SqlAlchemyStore:
    """Repository that can target SQLite, PostgreSQL, or another SQLAlchemy URL."""

    def __init__(self, database_url: str = DEFAULT_DATABASE_URL) -> None:
        engine_options: dict = {"future": True}
        if database_url.startswith("sqlite"):
            engine_options["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                engine_options["poolclass"] = StaticPool
        self.engine: Engine = create_engine(database_url, **engine_options)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        self._seed_if_empty()

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"

    def _seed_if_empty(self) -> None:
        with self.session_factory.begin() as session:
            if session.get(Household, "elm-street-home"):
                return
            session.add(Household(
                id="elm-street-home", name="Elm Street Home", invite_code="ELM-782",
                invite_link="https://grabtab.app/join/elm-782",
            ))
            session.add_all([
                User(id="anna", display_name="Anna", color="anna"),
                User(id="ben", display_name="Ben", color="ben"),
                User(id="clara", display_name="Clara", color="clara"),
            ])
            seed_time = datetime(2026, 9, 10, tzinfo=UTC)
            session.add_all([
                HouseholdMember(household_id="elm-street-home", user_id="anna", joined_at=seed_time),
                HouseholdMember(household_id="elm-street-home", user_id="ben", joined_at=seed_time),
                HouseholdMember(household_id="elm-street-home", user_id="clara", joined_at=seed_time),
                ShoppingItem(id="s1", household_id="elm-street-home", name="Oat milk", added_by_user_id="clara", created_at=seed_time),
                ShoppingItem(id="s2", household_id="elm-street-home", name="Toilet paper", added_by_user_id="anna", created_at=seed_time.replace(day=9)),
                ShoppingItem(id="s3", household_id="elm-street-home", name="Dishwasher tabs", added_by_user_id="ben", created_at=seed_time.replace(day=8)),
            ])
            expenses = [
                Expense(id="e1", household_id="elm-street-home", name="Internet", amount_cents=4200, paid_by_user_id="anna", source="direct", expense_date=date(2026, 9, 5), created_at=seed_time),
                Expense(id="e2", household_id="elm-street-home", name="Fresh produce", amount_cents=2840, paid_by_user_id="ben", source="shopping", expense_date=date(2026, 9, 8), created_at=seed_time.replace(day=9)),
                Expense(id="e3", household_id="elm-street-home", name="Cleaning supplies", amount_cents=1200, paid_by_user_id="clara", source="direct", expense_date=date(2026, 9, 9), created_at=seed_time.replace(day=8)),
            ]
            session.add_all(expenses)
            session.add_all([
                ExpenseParticipant(expense=expenses[0], user_id=user_id) for user_id in ("anna", "ben", "clara")
            ] + [
                ExpenseParticipant(expense=expenses[1], user_id=user_id) for user_id in ("anna", "ben", "clara")
            ] + [
                ExpenseParticipant(expense=expenses[2], user_id=user_id) for user_id in ("anna", "clara")
            ])

    def reset(self) -> None:
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        self._seed_if_empty()

    @staticmethod
    def _name(name: str) -> str:
        value = name.strip()
        if not value or len(value) > 60:
            raise DomainError(400, "Name must contain between 1 and 60 characters")
        return value

    @staticmethod
    def _cents(value: float) -> int:
        try:
            amount = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise DomainError(400, "Amount must be greater than zero") from None
        if not amount.is_finite() or amount <= 0:
            raise DomainError(400, "Amount must be greater than zero")
        return int(amount * 100)

    @staticmethod
    def _household_id(session: Session, user_id: str) -> str:
        membership = session.scalar(select(HouseholdMember).where(HouseholdMember.user_id == user_id))
        if membership is None:
            raise DomainError(401, "Authentication required")
        return membership.household_id

    def is_member(self, user_id: str) -> bool:
        with self.session_factory() as session:
            return session.scalar(select(HouseholdMember.user_id).where(HouseholdMember.user_id == user_id)) is not None

    def _participants(self, session: Session, household_id: str, participant_ids: list[str]) -> list[str]:
        if not participant_ids:
            raise DomainError(400, "Choose at least one participant")
        if len(set(participant_ids)) != len(participant_ids):
            raise DomainError(400, "Participants must be unique")
        members = set(session.scalars(select(HouseholdMember.user_id).where(HouseholdMember.household_id == household_id)))
        if not set(participant_ids).issubset(members):
            raise DomainError(400, "All participants must belong to your household")
        return participant_ids

    def household_state(self, current_user_id: str) -> dict:
        with self.session_factory() as session:
            household_id = self._household_id(session, current_user_id)
            household = session.get(Household, household_id)
            members = session.execute(
                select(User).join(HouseholdMember).where(HouseholdMember.household_id == household_id).order_by(HouseholdMember.joined_at, User.id)
            ).scalars().all()
            shopping = session.scalars(
                select(ShoppingItem).where(ShoppingItem.household_id == household_id, ShoppingItem.purchased_at.is_(None)).order_by(ShoppingItem.created_at.desc())
            ).all()
            expenses = session.scalars(
                select(Expense).where(Expense.household_id == household_id).order_by(Expense.created_at.desc())
            ).all()
            settlements = session.scalars(
                select(DebtSettlement).where(DebtSettlement.household_id == household_id).order_by(DebtSettlement.created_at.desc())
            ).all()
            return {
                "currentUserId": current_user_id,
                "household": {"name": household.name, "inviteCode": household.invite_code, "inviteLink": household.invite_link},
                "members": [{"id": member.id, "name": member.display_name, "color": member.color} for member in members],
                "shopping": [{"id": item.id, "name": item.name, "addedBy": item.added_by_user_id} for item in shopping],
                "expenses": [{"id": expense.id, "name": expense.name, "amount": expense.amount_cents / 100, "paidBy": expense.paid_by_user_id, "participants": [participant.user_id for participant in expense.participants], "createdAt": expense.expense_date.isoformat(), "source": expense.source} for expense in expenses],
                "settlements": [{"id": settlement.id, "from": settlement.from_user_id, "to": settlement.to_user_id} for settlement in settlements],
            }

    def add_shopping_item(self, user_id: str, name: str) -> None:
        with self.session_factory.begin() as session:
            household_id = self._household_id(session, user_id)
            session.add(ShoppingItem(id=self._new_id("s"), household_id=household_id, name=self._name(name), added_by_user_id=user_id))

    def purchase_item(self, user_id: str, item_id: str, amount: float) -> None:
        with self.session_factory.begin() as session:
            household_id = self._household_id(session, user_id)
            item = session.scalar(select(ShoppingItem).where(ShoppingItem.id == item_id, ShoppingItem.household_id == household_id, ShoppingItem.purchased_at.is_(None)).with_for_update())
            if item is None:
                raise DomainError(404, "Shopping item not found")
            participant_ids = list(session.scalars(select(HouseholdMember.user_id).where(HouseholdMember.household_id == household_id).order_by(HouseholdMember.joined_at)))
            expense = Expense(id=self._new_id("e"), household_id=household_id, name=item.name, amount_cents=self._cents(amount), paid_by_user_id=user_id, source="shopping", expense_date=date.today(), source_shopping_item_id=item.id)
            expense.participants = [ExpenseParticipant(user_id=member_id) for member_id in participant_ids]
            item.purchased_at = datetime.now(UTC)
            session.add(expense)

    def create_expense(self, user_id: str, name: str, amount: float, participant_ids: list[str]) -> None:
        with self.session_factory.begin() as session:
            household_id = self._household_id(session, user_id)
            participant_ids = self._participants(session, household_id, participant_ids)
            expense = Expense(id=self._new_id("e"), household_id=household_id, name=self._name(name), amount_cents=self._cents(amount), paid_by_user_id=user_id, source="direct", expense_date=date.today())
            expense.participants = [ExpenseParticipant(user_id=member_id) for member_id in participant_ids]
            session.add(expense)

    def _owned_expense(self, session: Session, user_id: str, household_id: str, expense_id: str) -> Expense:
        expense = session.scalar(select(Expense).where(Expense.id == expense_id, Expense.household_id == household_id))
        if expense is None:
            raise DomainError(404, "Expense not found")
        if expense.paid_by_user_id != user_id:
            raise DomainError(403, "You can only edit your own expenses")
        return expense

    def update_expense(self, user_id: str, expense_id: str, name: str, amount: float, participant_ids: list[str]) -> None:
        with self.session_factory.begin() as session:
            household_id = self._household_id(session, user_id)
            expense = self._owned_expense(session, user_id, household_id, expense_id)
            expense.name, expense.amount_cents = self._name(name), self._cents(amount)
            expense.participants = [ExpenseParticipant(user_id=member_id) for member_id in self._participants(session, household_id, participant_ids)]

    def delete_expense(self, user_id: str, expense_id: str) -> None:
        with self.session_factory.begin() as session:
            household_id = self._household_id(session, user_id)
            session.delete(self._owned_expense(session, user_id, household_id, expense_id))

    def _outstanding_debts(self, session: Session, household_id: str) -> set[tuple[str, str]]:
        member_ids = list(session.scalars(select(HouseholdMember.user_id).where(HouseholdMember.household_id == household_id).order_by(HouseholdMember.joined_at)))
        balances = {member_id: Decimal("0") for member_id in member_ids}
        expenses = session.scalars(select(Expense).where(Expense.household_id == household_id)).all()
        for expense in expenses:
            amount = Decimal(expense.amount_cents) / 100
            balances[expense.paid_by_user_id] += amount
            share = amount / len(expense.participants)
            for participant in expense.participants:
                balances[participant.user_id] -= share
        debtors = [[member_id, -balance] for member_id, balance in balances.items() if balance < 0]
        creditors = [[member_id, balance] for member_id, balance in balances.items() if balance > 0]
        debts: set[tuple[str, str]] = set()
        while debtors and creditors:
            debtor, creditor = debtors[0], creditors[0]
            debts.add((debtor[0], creditor[0]))
            paid = min(debtor[1], creditor[1])
            debtor[1] -= paid
            creditor[1] -= paid
            if debtor[1] == 0:
                debtors.pop(0)
            if creditor[1] == 0:
                creditors.pop(0)
        settled = set(session.execute(select(DebtSettlement.from_user_id, DebtSettlement.to_user_id).where(DebtSettlement.household_id == household_id)).all())
        return debts - settled

    def settle_debt(self, user_id: str, from_member_id: str, to_member_id: str) -> None:
        with self.session_factory.begin() as session:
            household_id = self._household_id(session, user_id)
            member_ids = set(session.scalars(select(HouseholdMember.user_id).where(HouseholdMember.household_id == household_id)))
            if from_member_id not in member_ids or to_member_id not in member_ids or from_member_id == to_member_id:
                raise DomainError(400, "Settlement members must be different household members")
            if (from_member_id, to_member_id) not in self._outstanding_debts(session, household_id):
                raise DomainError(400, "There is no outstanding debt for these members")
            session.add(DebtSettlement(id=self._new_id("st"), household_id=household_id, from_user_id=from_member_id, to_user_id=to_member_id, created_by_user_id=user_id))
