from fastapi.testclient import TestClient

from backend.app import create_app


def client() -> TestClient:
    return TestClient(create_app())


ANNA_HEADERS = {"Authorization": "Bearer mock-anna"}
BEN_HEADERS = {"Authorization": "Bearer mock-ben"}


def test_state_requires_authentication() -> None:
    response = client().get("/v1/household/state")

    assert response.status_code == 401
    assert response.json() == {"message": "Authentication required"}


def test_state_returns_authenticated_members_household() -> None:
    response = client().get("/v1/household/state", headers=ANNA_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["currentUserId"] == "anna"
    assert body["household"]["name"] == "Elm Street Home"
    assert [member["id"] for member in body["members"]] == ["anna", "ben", "clara"]
    assert len(body["shopping"]) == 3


def test_add_shopping_item_assigns_authenticated_user() -> None:
    response = client().post(
        "/v1/shopping-items", headers=BEN_HEADERS, json={"name": "  Kitchen roll  "}
    )

    assert response.status_code == 201
    assert response.json()["shopping"][0] == {
        "id": response.json()["shopping"][0]["id"],
        "name": "Kitchen roll",
        "addedBy": "ben",
    }


def test_buying_item_removes_it_and_creates_all_member_expense() -> None:
    response = client().post(
        "/v1/shopping-items/s2/purchase", headers=BEN_HEADERS, json={"amount": 4.5}
    )

    assert response.status_code == 200
    state = response.json()
    assert "s2" not in [item["id"] for item in state["shopping"]]
    assert state["expenses"][0] == {
        "id": state["expenses"][0]["id"],
        "name": "Toilet paper",
        "amount": 4.5,
        "paidBy": "ben",
        "participants": ["anna", "ben", "clara"],
        "createdAt": state["expenses"][0]["createdAt"],
        "source": "shopping",
    }


def test_add_direct_expense_uses_selected_participants() -> None:
    response = client().post(
        "/v1/expenses",
        headers=BEN_HEADERS,
        json={"name": "Cleaner", "amount": 12, "participantIds": ["anna", "ben"]},
    )

    assert response.status_code == 201
    expense = response.json()["expenses"][0]
    assert expense["name"] == "Cleaner"
    assert expense["paidBy"] == "ben"
    assert expense["participants"] == ["anna", "ben"]
    assert expense["source"] == "direct"


def test_expense_owner_can_update_and_delete() -> None:
    test_client = client()

    updated = test_client.patch(
        "/v1/expenses/e1",
        headers=ANNA_HEADERS,
        json={"name": "Broadband", "amount": 44, "participantIds": ["anna", "ben", "clara"]},
    )
    deleted = test_client.delete("/v1/expenses/e1", headers=ANNA_HEADERS)

    assert updated.status_code == 200
    assert updated.json()["expenses"][0]["name"] == "Broadband"
    assert deleted.status_code == 200
    assert "e1" not in [expense["id"] for expense in deleted.json()["expenses"]]


def test_non_owner_cannot_change_an_expense() -> None:
    test_client = client()
    payload = {"name": "Nope", "amount": 1, "participantIds": ["anna"]}

    update = test_client.patch("/v1/expenses/e1", headers=BEN_HEADERS, json=payload)
    deletion = test_client.delete("/v1/expenses/e1", headers=BEN_HEADERS)

    assert update.status_code == 403
    assert deletion.status_code == 403
    assert update.json()["message"] == "You can only edit your own expenses"


def test_rejects_invalid_expense_participants() -> None:
    response = client().post(
        "/v1/expenses",
        headers=ANNA_HEADERS,
        json={"name": "Lamp", "amount": 10, "participantIds": ["not-a-member"]},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "All participants must belong to your household"


def test_settlement_is_recorded_for_household_members() -> None:
    response = client().post(
        "/v1/debt-settlements",
        headers=ANNA_HEADERS,
        json={"fromMemberId": "clara", "toMemberId": "anna"},
    )

    assert response.status_code == 201
    settlement = response.json()["settlements"][0]
    assert settlement["from"] == "clara"
    assert settlement["to"] == "anna"


def test_reset_demo_data_restores_seeded_state() -> None:
    test_client = client()
    test_client.post("/v1/shopping-items", headers=ANNA_HEADERS, json={"name": "Coffee"})

    response = test_client.post("/v1/dev/reset-demo-data", headers=ANNA_HEADERS)

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["shopping"]] == [
        "Oat milk",
        "Toilet paper",
        "Dishwasher tabs",
    ]
