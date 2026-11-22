"""Authentication endpoints for user registration, login, and profile lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from src.api.v1.schemas import (
    COMMON_ERROR_RESPONSES,
    STANDARD_400_RESPONSE,
    STANDARD_401_RESPONSE,
    STANDARD_422_RESPONSE,
    MembershipSummary,
    TokenResponse,
    UserProfileResponse,
    UserRegisterRequest,
    UserResponse,
)
from src.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.core.database import get_db
from src.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from src.models.entities import Membership, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Create a new user with username, unique email, and hashed password.",
    responses={
        status.HTTP_200_OK: {
            "model": UserResponse,
            "description": "User account created successfully.",
        },
        **STANDARD_400_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a new user account."""
    existing_user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == payload.username.strip().lower(),
                func.lower(User.email) == payload.email.strip().lower(),
            )
        )
    )
    if existing_user:
        if existing_user.username.lower() == payload.username.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{payload.username}' is already taken",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{payload.email}' is already registered",
        )

    new_user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        hashed_password=hash_password(payload.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT token",
    description=(
        "Authenticate using username or email along with password. "
        "Accepts either JSON payload or OAuth2 form data."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate credentials and issue signed JWT access token."""
    content_type = request.headers.get("content-type", "")
    username_or_email = ""
    password = ""

    if "application/json" in content_type:
        try:
            body = await request.json()
            username_or_email = (
                body.get("username", "")
                or body.get("email", "")
                or body.get("identifier", "")
            )
            password = body.get("password", "")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed JSON body",
            )
    else:
        try:
            form = await request.form()
            username_or_email = str(form.get("username", ""))
            password = str(form.get("password", ""))
        except Exception:
            from urllib.parse import parse_qs

            raw_body = (await request.body()).decode("utf-8")
            parsed = parse_qs(raw_body)
            username_or_email = parsed.get("username", [""])[0]
            password = parsed.get("password", [""])[0]

    username_or_email = username_or_email.strip()
    if not username_or_email or not password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username and password are required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    lookup = username_or_email.lower()
    user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.username) == lookup,
                func.lower(User.email) == lookup,
            )
        )
    )
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "email": user.email}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile & memberships",
    description=(
        "Retrieve the authenticated user identity and all active "
        "household memberships."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Return caller's profile and household memberships."""
    memberships = db.scalars(
        select(Membership)
        .where(Membership.user_id == current_user.id)
        .options(selectinload(Membership.home))
    ).all()

    membership_summaries: list[MembershipSummary] = []
    for m in memberships:
        home_name = m.home.name if m.home else "Household"
        membership_summaries.append(
            MembershipSummary(
                id=m.id,
                home_id=m.home_id,
                home_name=home_name,
                role=m.role,
                joined_at=m.created_at,
            )
        )

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        memberships=membership_summaries,
    )
