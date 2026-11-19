"""Security utilities, password hashing, JWT operations, and auth dependencies."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)
from src.core.database import get_db
from src.models.entities import Home, Membership, User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    description="OAuth2 Password Bearer token authentication.",
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: Raw plaintext password string.

    Returns:
        Bcrypt hashed password string.
    """
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: Raw plaintext password attempt.
        hashed_password: Stored bcrypt hashed password string.

    Returns:
        True if password matches, False otherwise.
    """
    pwd_bytes = plain_password.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode payload claims into a signed JWT access token.

    Args:
        data: Claims dictionary (must contain 'sub' user identifier).
        expires_delta: Optional custom lifetime duration.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now_utc})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Args:
        token: Raw JWT Bearer token string.

    Returns:
        Decoded payload claims dictionary.

    Raises:
        HTTPException: If token is expired or invalid.
    """
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency extracting and verifying the authenticated user from JWT token.

    Args:
        token: Injected JWT Bearer token from Authorization header.
        db: Database session.

    Returns:
        Active authenticated User entity.

    Raises:
        HTTPException: 401 if token is invalid or user does not exist.
    """
    payload = decode_access_token(token)
    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.scalar(select(User).where(User.id == user_uuid))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def verify_home_membership(
    home_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Membership:
    """Dependency verifying that the authenticated user belongs to the target home.

    Args:
        home_id: Target household UUID from path parameter.
        current_user: Authenticated caller from JWT token.
        db: Database session.

    Returns:
        Membership record confirming active household access.

    Raises:
        HTTPException: 404 if home does not exist.
        HTTPException: 403 if user is not a member of the household.
    """
    home = db.scalar(select(Home).where(Home.id == home_id))
    if home is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Household with ID '{home_id}' not found",
        )

    membership = db.scalar(
        select(Membership).where(
            Membership.home_id == home_id,
            Membership.user_id == current_user.id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of this household",
        )
    return membership


def require_home_buyer(
    membership: Membership = Depends(verify_home_membership),
) -> Membership:
    """Dependency asserting the user holds the 'buyer' role within the household.

    Args:
        membership: Injected verified membership.

    Returns:
        Membership record confirming buyer privileges.

    Raises:
        HTTPException: 403 if user is only a 'consumer'.
    """
    if membership.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Action requires 'buyer' role in this household",
        )
    return membership
