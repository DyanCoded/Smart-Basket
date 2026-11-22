"""Integration tests for JWT authentication, user registration, and household RBAC.

Covers Issue #15 acceptance criteria:
- Password hashing & JWT token validation (src/core/security.py)
- User registration and login (POST /api/v1/auth/register, /api/v1/auth/login)
- Authenticated user profile (GET /api/v1/auth/me)
- Household creation with auto-assigned buyer role (POST /api/v1/homes)
- Household listings (GET /api/v1/homes)
- Household detail & roster (GET /api/v1/homes/{home_id})
- Membership dependency guard & unauthorized household access (403 Forbidden)
- Role-based membership invitations & member removals
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from src.core.config import JWT_ALGORITHM
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_security_hashing_and_jwt_tokens() -> None:
    """Verify password hashing with bcrypt and JWT creation/validation."""
    raw_password = "SuperSecretPassword123!"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$2b$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False

    # Valid JWT creation & decoding
    token = create_access_token(
        data={"sub": "11111111-2222-3333-4444-555555555555", "username": "testuser"}
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "11111111-2222-3333-4444-555555555555"
    assert payload["username"] == "testuser"

    # Expired token raises 401
    expired_token = create_access_token(
        data={"sub": "11111111-2222-3333-4444-555555555555"},
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(Exception) as exc_info:
        decode_access_token(expired_token)
    assert "expired" in str(exc_info.value.detail).lower()

    # Tampered / invalid token raises 401
    bad_token = jwt.encode(
        {"sub": "attacker"}, "wrong_secret_key_123456789012345", algorithm=JWT_ALGORITHM
    )
    with pytest.raises(Exception) as exc_info:
        decode_access_token(bad_token)
    assert "credentials" in str(exc_info.value.detail).lower()


def test_user_registration_success_and_duplicates(client: TestClient) -> None:
    """Verify registration creates user and rejects duplicate usernames/emails."""
    # 1. Register User A
    res = client.post(
        "/api/v1/auth/register",
        json={
            "username": "sarah_shopper",
            "email": "sarah@example.com",
            "password": "Password123!",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "sarah_shopper"
    assert data["email"] == "sarah@example.com"
    assert "id" in data

    # 2. Duplicate username rejected
    res_dup_user = client.post(
        "/api/v1/auth/register",
        json={
            "username": "sarah_shopper",
            "email": "different_email@example.com",
            "password": "Password123!",
        },
    )
    assert res_dup_user.status_code == 400
    assert "already taken" in res_dup_user.json()["detail"].lower()

    # 3. Duplicate email rejected
    res_dup_email = client.post(
        "/api/v1/auth/register",
        json={
            "username": "different_username",
            "email": "sarah@example.com",
            "password": "Password123!",
        },
    )
    assert res_dup_email.status_code == 400
    assert "already registered" in res_dup_email.json()["detail"].lower()


def test_user_login_json_and_form(client: TestClient) -> None:
    """Verify login works with both JSON payloads and form-encoded data."""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "login_user",
            "email": "login_user@example.com",
            "password": "CorrectPassword123!",
        },
    )

    # 1. Login with JSON payload (using username)
    res_json = client.post(
        "/api/v1/auth/login",
        json={
            "username": "login_user",
            "password": "CorrectPassword123!",
        },
    )
    assert res_json.status_code == 200
    data_json = res_json.json()
    assert "access_token" in data_json
    assert data_json["token_type"] == "bearer"
    assert data_json["expires_in"] == 3600

    # 2. Login with JSON payload (using email)
    res_email = client.post(
        "/api/v1/auth/login",
        json={
            "username": "login_user@example.com",
            "password": "CorrectPassword123!",
        },
    )
    assert res_email.status_code == 200
    assert "access_token" in res_email.json()

    # 3. Login with form-data (Swagger OAuth2 compatibility)
    res_form = client.post(
        "/api/v1/auth/login",
        data={
            "username": "login_user",
            "password": "CorrectPassword123!",
        },
    )
    assert res_form.status_code == 200
    assert "access_token" in res_form.json()

    # 4. Incorrect password returns 401
    res_bad_pw = client.post(
        "/api/v1/auth/login",
        json={
            "username": "login_user",
            "password": "WrongPassword!",
        },
    )
    assert res_bad_pw.status_code == 401
    assert "incorrect" in res_bad_pw.json()["detail"].lower()

    # 5. Non-existent user returns 401
    res_non_existent = client.post(
        "/api/v1/auth/login",
        json={
            "username": "non_existent_user",
            "password": "SomePassword123!",
        },
    )
    assert res_non_existent.status_code == 401


def test_auth_me_endpoint(client: TestClient) -> None:
    """Verify /api/v1/auth/me requires valid token and returns profile."""
    # 1. Unauthenticated request rejected
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401

    # 2. Authenticated request succeeds
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "profile_user",
            "email": "profile@example.com",
            "password": "Password123!",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "profile_user", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    res_auth = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_auth.status_code == 200
    profile = res_auth.json()
    assert profile["username"] == "profile_user"
    assert profile["email"] == "profile@example.com"
    assert isinstance(profile["memberships"], list)


def test_create_home_and_auto_assign_buyer(client: TestClient) -> None:
    """Verify creating a home auto-assigns the creator as 'buyer'."""
    # Register & Login
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "home_owner",
            "email": "owner@example.com",
            "password": "Password123!",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "home_owner", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Create household
    res_home = client.post(
        "/api/v1/homes",
        json={"name": "Sunnyvale Apartment"},
        headers=auth_header,
    )
    assert res_home.status_code == 201
    home_data = res_home.json()
    assert home_data["name"] == "Sunnyvale Apartment"
    assert home_data["role"] == "buyer"
    assert len(home_data["members"]) == 1
    assert home_data["members"][0]["username"] == "home_owner"
    assert home_data["members"][0]["role"] == "buyer"

    # List households for user
    res_list = client.get("/api/v1/homes", headers=auth_header)
    assert res_list.status_code == 200
    homes_list = res_list.json()
    assert len(homes_list) >= 1
    target = next(h for h in homes_list if h["id"] == home_data["id"])
    assert target["name"] == "Sunnyvale Apartment"
    assert target["role"] == "buyer"


def test_household_unauthorized_access_403(client: TestClient) -> None:
    """Verify membership dependency guard blocks non-member access with 403."""
    # User A creates Home A
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "user_a",
            "email": "a@example.com",
            "password": "Password123!",
        },
    )
    login_a = client.post(
        "/api/v1/auth/login", json={"username": "user_a", "password": "Password123!"}
    )
    token_a = login_a.json()["access_token"]
    res_home = client.post(
        "/api/v1/homes",
        json={"name": "Private Sanctuary"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    home_id = res_home.json()["id"]

    # User B registers and attempts to access Home A
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "user_b",
            "email": "b@example.com",
            "password": "Password123!",
        },
    )
    login_b = client.post(
        "/api/v1/auth/login", json={"username": "user_b", "password": "Password123!"}
    )
    token_b = login_b.json()["access_token"]

    # User B accessing Home A -> 403 Forbidden!
    res_forbidden = client.get(
        f"/api/v1/homes/{home_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_forbidden.status_code == 403
    assert "not a member" in res_forbidden.json()["detail"].lower()

    # Non-existent home ID -> 404 Not Found
    random_id = str(uuid.uuid4())
    res_not_found = client.get(
        f"/api/v1/homes/{random_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_not_found.status_code == 404


def test_invite_and_manage_household_members(client: TestClient) -> None:
    """Verify buyer can invite members, and consumers cannot invite others."""
    # Register Buyer (User A) and Consumer (User B)
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "buyer_alice",
            "email": "alice_buyer@example.com",
            "password": "Password123!",
        },
    )
    login_a = client.post(
        "/api/v1/auth/login",
        json={"username": "buyer_alice", "password": "Password123!"},
    )
    token_a = login_a.json()["access_token"]
    header_a = {"Authorization": f"Bearer {token_a}"}

    client.post(
        "/api/v1/auth/register",
        json={
            "username": "consumer_bob",
            "email": "bob_consumer@example.com",
            "password": "Password123!",
        },
    )
    login_b = client.post(
        "/api/v1/auth/login",
        json={"username": "consumer_bob", "password": "Password123!"},
    )
    token_b = login_b.json()["access_token"]
    header_b = {"Authorization": f"Bearer {token_b}"}

    # Buyer creates Home
    home_res = client.post(
        "/api/v1/homes", json={"name": "Family Villa"}, headers=header_a
    )
    home_id = home_res.json()["id"]

    # 1. Buyer invites Bob as 'consumer'
    invite_res = client.post(
        f"/api/v1/homes/{home_id}/members",
        json={"username": "consumer_bob", "role": "consumer"},
        headers=header_a,
    )
    assert invite_res.status_code == 201
    member_data = invite_res.json()
    assert member_data["username"] == "consumer_bob"
    assert member_data["role"] == "consumer"

    # 2. Bob can now access the home
    res_bob_access = client.get(f"/api/v1/homes/{home_id}", headers=header_b)
    assert res_bob_access.status_code == 200
    assert len(res_bob_access.json()["members"]) == 2

    # 3. Duplicate invite returns 400
    res_dup = client.post(
        f"/api/v1/homes/{home_id}/members",
        json={"email": "bob_consumer@example.com", "role": "consumer"},
        headers=header_a,
    )
    assert res_dup.status_code == 400
    assert "already a member" in res_dup.json()["detail"].lower()

    # 4. Bob (consumer) attempts to invite someone else -> 403 Forbidden!
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "charlie_third",
            "email": "charlie@example.com",
            "password": "Password123!",
        },
    )
    res_unauth_invite = client.post(
        f"/api/v1/homes/{home_id}/members",
        json={"username": "charlie_third", "role": "consumer"},
        headers=header_b,
    )
    assert res_unauth_invite.status_code == 403
    assert "buyers can invite" in res_unauth_invite.json()["detail"].lower()


def test_remove_household_member(client: TestClient) -> None:
    """Verify buyer can remove a member from household."""
    # Setup Home with Owner (Buyer) and Member (Consumer)
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "owner_dave",
            "email": "dave@example.com",
            "password": "Password123!",
        },
    )
    token_dave = client.post(
        "/api/v1/auth/login",
        json={"username": "owner_dave", "password": "Password123!"},
    ).json()["access_token"]
    header_dave = {"Authorization": f"Bearer {token_dave}"}

    client.post(
        "/api/v1/auth/register",
        json={
            "username": "temp_guest",
            "email": "guest@example.com",
            "password": "Password123!",
        },
    )
    login_guest = client.post(
        "/api/v1/auth/login",
        json={"username": "temp_guest", "password": "Password123!"},
    ).json()
    token_guest = login_guest["access_token"]
    guest_profile = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_guest}"}
    ).json()
    guest_id = guest_profile["id"]

    home_res = client.post(
        "/api/v1/homes", json={"name": "Guest Cottage"}, headers=header_dave
    )
    home_id = home_res.json()["id"]

    # Add guest
    client.post(
        f"/api/v1/homes/{home_id}/members",
        json={"user_id": guest_id, "role": "consumer"},
        headers=header_dave,
    )

    # Confirm guest has access
    assert (
        client.get(
            f"/api/v1/homes/{home_id}",
            headers={"Authorization": f"Bearer {token_guest}"},
        ).status_code
        == 200
    )

    # Owner removes guest via path parameter
    del_res = client.delete(
        f"/api/v1/homes/{home_id}/members/{guest_id}",
        headers=header_dave,
    )
    assert del_res.status_code == 200

    # Guest now gets 403 Forbidden!
    assert (
        client.get(
            f"/api/v1/homes/{home_id}",
            headers={"Authorization": f"Bearer {token_guest}"},
        ).status_code
        == 403
    )


def test_login_accepts_case_insensitive_username_and_email(
    client: TestClient,
) -> None:
    """Verify login accepts username or email cleanly regardless of casing."""
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "CaseUser1",
            "email": "CaseUser1@SmartBasket.local",
            "password": "TestPass123!",
        },
    )

    for payload in (
        {"username": "caseuser1", "password": "TestPass123!"},
        {"username": "CASEUSER1", "password": "TestPass123!"},
        {"email": "caseuser1@smartbasket.local", "password": "TestPass123!"},
        {"identifier": "CASEUSER1@SMARTBASKET.LOCAL", "password": "TestPass123!"},
    ):
        res = client.post("/api/v1/auth/login", json=payload)
        assert res.status_code == 200
        assert "access_token" in res.json()


def test_join_home_by_unique_id(client: TestClient) -> None:
    """Verify POST /api/v1/homes/join joins existing home by UUID with role."""
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "join_owner",
            "email": "join_owner@smartbasket.local",
            "password": "TestPass123!",
        },
    )
    owner_token = client.post(
        "/api/v1/auth/login",
        json={"username": "join_owner", "password": "TestPass123!"},
    ).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Owner creates a home (with explicit role='buyer')
    home_res = client.post(
        "/api/v1/homes",
        json={"name": "Shared Family Home", "role": "buyer"},
        headers=owner_headers,
    )
    assert home_res.status_code == 201
    home_id = home_res.json()["id"]

    # Second user registers and joins via unique Home ID
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "join_member",
            "email": "join_member@smartbasket.local",
            "password": "TestPass123!",
        },
    )
    member_token = client.post(
        "/api/v1/auth/login",
        json={"username": "join_member", "password": "TestPass123!"},
    ).json()["access_token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}

    join_res = client.post(
        "/api/v1/homes/join",
        json={"home_id": home_id, "role": "consumer"},
        headers=member_headers,
    )
    assert join_res.status_code == 201
    joined = join_res.json()
    assert joined["id"] == home_id
    assert joined["role"] == "consumer"
    assert len(joined["members"]) == 2
    assert any(
        m["username"] == "join_member" and m["role"] == "consumer"
        for m in joined["members"]
    )

    # Duplicate join rejected cleanly with 400
    dup_res = client.post(
        "/api/v1/homes/join",
        json={"home_id": home_id, "role": "buyer"},
        headers=member_headers,
    )
    assert dup_res.status_code == 400
    assert "already a member" in dup_res.json()["detail"].lower()

    # Nonexistent Home ID returns 404
    missing_res = client.post(
        "/api/v1/homes/join",
        json={"home_id": str(uuid.uuid4()), "role": "consumer"},
        headers=member_headers,
    )
    assert missing_res.status_code == 404


def test_seed_users_reset_preserves_catalog_and_seeds_demo_home(
    db_session,
) -> None:
    """Verify seed_users.py --reset preserves products/prices & seeds 3 accounts."""
    from sqlalchemy import func, select

    from scripts.seed_users import DEMO_HOME_ID, seed_users_database
    from src.models.entities import Membership, Product, StorePrice, User

    initial_products = db_session.scalar(select(func.count(Product.id)))
    initial_prices = db_session.scalar(select(func.count(StorePrice.id)))
    assert initial_products == 18
    assert initial_prices == 90

    result = seed_users_database(db_session, reset=True, commit=False)
    assert result["home_id"] == str(DEMO_HOME_ID)
    assert result["users_created"] == 3
    assert result["memberships_created"] == 3

    # Catalog strictly untouched
    assert db_session.scalar(select(func.count(Product.id))) == initial_products
    assert db_session.scalar(select(func.count(StorePrice.id))) == initial_prices

    # All 3 accounts exist with expected roles
    users = db_session.scalars(select(User)).all()
    assert {u.username for u in users} == {"buyer1", "consumer1", "consumer2"}
    memberships = db_session.scalars(
        select(Membership).where(Membership.home_id == DEMO_HOME_ID)
    ).all()
    assert len(memberships) == 3

    # Idempotent second run without --reset creates 0 duplicates
    second = seed_users_database(db_session, reset=False, commit=False)
    assert second["users_created"] == 0
    assert second["memberships_created"] == 0
