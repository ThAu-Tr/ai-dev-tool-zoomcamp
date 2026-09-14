from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.store import DEFAULT_DATABASE_URL, DomainError, SqlAlchemyStore


class ShoppingItemCreate(BaseModel):
    name: str


class PurchaseCreate(BaseModel):
    amount: float = Field(gt=0)


class ExpensePayload(BaseModel):
    name: str
    amount: float = Field(gt=0)
    participantIds: list[str]


class SettlementCreate(BaseModel):
    fromMemberId: str
    toMemberId: str


bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def create_app(database_url: str = DEFAULT_DATABASE_URL) -> FastAPI:
    database = SqlAlchemyStore(database_url)
    app = FastAPI(title="GrabTab API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def current_user(credentials: Credentials) -> str:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise DomainError(401, "Authentication required")
        token_to_user = {"mock-anna": "anna", "mock-ben": "ben", "mock-clara": "clara"}
        user_id = token_to_user.get(credentials.credentials)
        if user_id is None or not database.is_member(user_id):
            raise DomainError(401, "Authentication required")
        return user_id

    User = Annotated[str, Depends(current_user)]

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"message": "Invalid request"})

    @app.get("/v1/household/state")
    def get_household_state(user_id: User) -> dict:
        return database.household_state(user_id)

    @app.post("/v1/shopping-items", status_code=201)
    def add_shopping_item(payload: ShoppingItemCreate, user_id: User) -> dict:
        database.add_shopping_item(user_id, payload.name)
        return database.household_state(user_id)

    @app.post("/v1/shopping-items/{item_id}/purchase")
    def buy_shopping_item(item_id: str, payload: PurchaseCreate, user_id: User) -> dict:
        database.purchase_item(user_id, item_id, payload.amount)
        return database.household_state(user_id)

    @app.post("/v1/expenses", status_code=201)
    def add_expense(payload: ExpensePayload, user_id: User) -> dict:
        database.create_expense(user_id, payload.name, payload.amount, payload.participantIds)
        return database.household_state(user_id)

    @app.patch("/v1/expenses/{expense_id}")
    def update_expense(expense_id: str, payload: ExpensePayload, user_id: User) -> dict:
        database.update_expense(user_id, expense_id, payload.name, payload.amount, payload.participantIds)
        return database.household_state(user_id)

    @app.delete("/v1/expenses/{expense_id}")
    def delete_expense(expense_id: str, user_id: User) -> dict:
        database.delete_expense(user_id, expense_id)
        return database.household_state(user_id)

    @app.post("/v1/debt-settlements", status_code=201)
    def settle_debt(payload: SettlementCreate, user_id: User) -> dict:
        database.settle_debt(user_id, payload.fromMemberId, payload.toMemberId)
        return database.household_state(user_id)

    @app.post("/v1/dev/reset-demo-data")
    def reset_demo_data(user_id: User) -> dict:
        database.reset()
        return database.household_state(user_id)

    return app


app = create_app()
