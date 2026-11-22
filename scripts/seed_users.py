"""Mock multi-phone test user & Demo Family Home seeder for SmartBasket.

Safely clears user/household tables (`pantry_logs`, `pantry_items`,
`basket_items`, `baskets`, `memberships`, `homes`, `users`) when `--reset` is
passed while preserving the entire product catalog (`retailers`, `stores`,
`categories`, `products`, `store_prices`, `price_history`).

Usage:
    python scripts/seed_users.py --reset
    python scripts/seed_users.py
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import delete, func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from src.core.database import SessionLocal  # noqa: E402
from src.core.security import hash_password  # noqa: E402
from src.models.entities import (  # noqa: E402
    Basket,
    BasketItem,
    Home,
    Membership,
    PantryItem,
    PantryLog,
    User,
)

DEMO_HOME_NAMESPACE = uuid.NAMESPACE_URL
DEMO_HOME_ID = uuid.uuid5(
    DEMO_HOME_NAMESPACE, "https://smartbasket.co.za/home:demo-family-home"
)
DEMO_HOME_NAME = "Demo Family Home"


@dataclass(frozen=True)
class MockTestAccount:
    username: str
    email: str
    password: str
    role: str


# PLACEHOLDER_ multi-phone local testing credentials (non-personal .local accounts)
DEMO_TEST_ACCOUNTS: tuple[MockTestAccount, ...] = (
    MockTestAccount(
        username="buyer1",
        email="buyer1@smartbasket.local",
        password="TestPass123!",
        role="buyer",
    ),
    MockTestAccount(
        username="consumer1",
        email="consumer1@smartbasket.local",
        password="TestPass123!",
        role="consumer",
    ),
    MockTestAccount(
        username="consumer2",
        email="consumer2@smartbasket.local",
        password="TestPass123!",
        role="consumer",
    ),
)


def seed_users_database(
    session: Session,
    *,
    reset: bool = False,
    commit: bool = True,
) -> dict[str, object]:
    """Seed Demo Family Home and 3 multi-phone test accounts (keeps catalog intact)."""
    if reset:
        # Delete strictly in FK-safe order; preserve retailers/stores/products/prices
        session.execute(delete(PantryLog))
        session.execute(delete(PantryItem))
        session.execute(delete(BasketItem))
        session.execute(delete(Basket))
        session.execute(delete(Membership))
        session.execute(delete(Home))
        session.execute(delete(User))
        session.flush()

    home = session.scalar(select(Home).where(Home.id == DEMO_HOME_ID))
    if home is None:
        home = Home(id=DEMO_HOME_ID, name=DEMO_HOME_NAME)
        session.add(home)
        session.flush()

    users_created = 0
    memberships_created = 0

    for account in DEMO_TEST_ACCOUNTS:
        user = session.scalar(
            select(User).where(func.lower(User.email) == account.email.lower())
        )
        if user is None:
            user = User(
                username=account.username,
                email=account.email.lower(),
                hashed_password=hash_password(account.password),
            )
            session.add(user)
            session.flush()
            users_created += 1

        membership = session.scalar(
            select(Membership).where(
                Membership.home_id == home.id,
                Membership.user_id == user.id,
            )
        )
        if membership is None:
            session.add(
                Membership(
                    user_id=user.id,
                    home_id=home.id,
                    role=account.role,
                )
            )
            memberships_created += 1

    session.flush()
    if commit:
        session.commit()

    return {
        "home_id": str(home.id),
        "home_name": home.name,
        "users_created": users_created,
        "memberships_created": memberships_created,
        "accounts": DEMO_TEST_ACCOUNTS,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Seed Demo Family Home & multi-phone test accounts "
            "(preserves products and store_prices)."
        )
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Clear pantry_logs, pantry_items, basket_items, baskets, "
            "memberships, homes, and users before seeding."
        ),
    )
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        result = seed_users_database(session, reset=args.reset, commit=True)
    finally:
        session.close()

    print("=" * 78)
    print("SmartBasket Multi-Phone Test Users Seeded")
    print("=" * 78)
    print(f"Household Name : {result['home_name']}")
    print(f"Unique Home ID : {result['home_id']}")
    print("-" * 78)
    print(f"{'Username':<14} {'Email':<28} {'Password':<16} {'Role':<10}")
    print("-" * 78)
    for account in DEMO_TEST_ACCOUNTS:
        print(
            f"{account.username:<14} {account.email:<28} "
            f"{account.password:<16} {account.role:<10}"
        )
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
