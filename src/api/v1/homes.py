"""Household and family pantry management endpoints."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from src.api.v1.schemas import (
    COMMON_ERROR_RESPONSES,
    STANDARD_400_RESPONSE,
    STANDARD_401_RESPONSE,
    STANDARD_403_RESPONSE,
    STANDARD_404_RESPONSE,
    STANDARD_422_RESPONSE,
    AddMemberRequest,
    HomeCreateRequest,
    HomeDetailResponse,
    HomeMemberResponse,
    HomeResponse,
)
from src.core.database import get_db
from src.core.security import get_current_user, verify_home_membership
from src.models.entities import Home, Membership, User

router = APIRouter(prefix="/homes", tags=["homes"])


@router.get(
    "",
    response_model=List[HomeResponse],
    summary="List caller's households",
    description="Retrieve all households in which the authenticated user is a member.",
    responses={
        **STANDARD_401_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def list_homes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[HomeResponse]:
    """Return all homes associated with current user."""
    memberships = db.scalars(
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .options(
            selectinload(Membership.home).selectinload(Home.memberships),
        )
    ).all()

    results: list[HomeResponse] = []
    for m in memberships:
        if m.home:
            member_count = len(m.home.memberships) if m.home.memberships else 1
            results.append(
                HomeResponse(
                    id=m.home.id,
                    name=m.home.name,
                    created_at=m.home.created_at,
                    role=m.role,
                    member_count=member_count,
                )
            )
    return results


@router.post(
    "",
    response_model=HomeDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new household",
    description=(
        "Create a household space and automatically assign the creator "
        "as the initial 'buyer'."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": HomeDetailResponse,
            "description": "Household created successfully.",
        },
        **STANDARD_400_RESPONSE,
        **STANDARD_401_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def create_home(
    payload: HomeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HomeDetailResponse:
    """Create a home and auto-assign caller as buyer."""
    home_name = payload.name.strip()
    if not home_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Household name cannot be empty",
        )

    home = Home(name=home_name)
    db.add(home)
    db.flush()

    membership = Membership(
        user_id=current_user.id,
        home_id=home.id,
        role="buyer",
    )
    db.add(membership)
    db.commit()
    db.refresh(home)

    initial_member = HomeMemberResponse(
        id=membership.id,
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role="buyer",
        joined_at=membership.created_at,
    )

    return HomeDetailResponse(
        id=home.id,
        name=home.name,
        created_at=home.created_at,
        role="buyer",
        members=[initial_member],
    )


@router.get(
    "/{home_id}",
    response_model=HomeDetailResponse,
    summary="Get household details and member roster",
    description=(
        "Retrieve household details including full roster of buyers " "and consumers."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def get_home_detail(
    home_id: uuid.UUID,
    membership: Membership = Depends(verify_home_membership),
    db: Session = Depends(get_db),
) -> HomeDetailResponse:
    """Return household details if caller is an authorized member."""
    home = db.scalar(
        select(Home)
        .where(Home.id == home_id)
        .options(
            selectinload(Home.memberships).selectinload(Membership.user),
        )
    )
    if not home:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Household not found",
        )

    members_list: list[HomeMemberResponse] = []
    for m in home.memberships:
        if m.user:
            members_list.append(
                HomeMemberResponse(
                    id=m.id,
                    user_id=m.user.id,
                    username=m.user.username,
                    email=m.user.email,
                    role=m.role,
                    joined_at=m.created_at,
                )
            )

    return HomeDetailResponse(
        id=home.id,
        name=home.name,
        created_at=home.created_at,
        role=membership.role,
        members=members_list,
    )


@router.post(
    "/{home_id}/members",
    response_model=HomeMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite/add a member to household",
    description=(
        "Add a user to a household with 'buyer' or 'consumer' role. "
        "Requires caller to hold 'buyer' role."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": HomeMemberResponse,
            "description": "Member added to household successfully.",
        },
        **STANDARD_400_RESPONSE,
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def add_home_member(
    home_id: uuid.UUID,
    payload: AddMemberRequest,
    membership: Membership = Depends(verify_home_membership),
    db: Session = Depends(get_db),
) -> HomeMemberResponse:
    """Add a member to the household."""
    if membership.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only household buyers can invite or add members",
        )

    assigned_role = payload.role.strip().lower()
    if assigned_role not in ("buyer", "consumer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'buyer' or 'consumer'",
        )

    # Locate target user
    target_user: Optional[User] = None
    if payload.user_id:
        target_user = db.scalar(select(User).where(User.id == payload.user_id))
    elif payload.username or payload.email:
        query_parts = []
        if payload.username:
            query_parts.append(User.username == payload.username.strip())
        if payload.email:
            query_parts.append(User.email == payload.email.strip().lower())
        target_user = db.scalar(select(User).where(or_(*query_parts)))

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User to invite was not found",
        )

    # Check if already a member
    existing_m = db.scalar(
        select(Membership).where(
            Membership.home_id == home_id,
            Membership.user_id == target_user.id,
        )
    )
    if existing_m:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"User '{target_user.username}' is already a member "
                "of this household"
            ),
        )

    new_membership = Membership(
        user_id=target_user.id,
        home_id=home_id,
        role=assigned_role,
    )
    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    return HomeMemberResponse(
        id=new_membership.id,
        user_id=target_user.id,
        username=target_user.username,
        email=target_user.email,
        role=new_membership.role,
        joined_at=new_membership.created_at,
    )


def _remove_member_core(
    home_id: uuid.UUID,
    target_user_id: uuid.UUID,
    membership: Membership,
    current_user: User,
    db: Session,
) -> dict[str, str]:
    """Shared logic for removing a household member."""
    # Buyers can remove any member; non-buyers can only remove themselves
    if membership.role != "buyer" and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only buyers can remove other members",
        )

    target_membership = db.scalar(
        select(Membership).where(
            Membership.home_id == home_id,
            Membership.user_id == target_user_id,
        )
    )
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user is not a member of this household",
        )

    db.delete(target_membership)
    db.commit()
    return {"detail": "Member removed from household successfully"}


@router.delete(
    "/{home_id}/members/{user_id}",
    summary="Remove a member from household by user ID",
    description=(
        "Remove a user from household. Buyers can remove anyone; "
        "members can remove themselves."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def remove_home_member_path(
    home_id: uuid.UUID,
    user_id: uuid.UUID,
    membership: Membership = Depends(verify_home_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove member by user ID path parameter."""
    return _remove_member_core(
        home_id=home_id,
        target_user_id=user_id,
        membership=membership,
        current_user=current_user,
        db=db,
    )


@router.delete(
    "/{home_id}/members",
    summary="Remove a member from household via query parameter",
    description="Remove a user from household using user_id query parameter.",
    responses={
        **STANDARD_400_RESPONSE,
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def remove_home_member_query(
    home_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(default=None, description="User ID to remove"),
    membership: Membership = Depends(verify_home_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove member by query parameter."""
    target_id = user_id or current_user.id
    return _remove_member_core(
        home_id=home_id,
        target_user_id=target_id,
        membership=membership,
        current_user=current_user,
        db=db,
    )
