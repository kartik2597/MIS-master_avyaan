from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserUpdate


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower())
    return db.scalar(statement)


def list_users(db: Session) -> list[User]:
    """Every user, newest first."""
    return list(db.scalars(select(User).order_by(User.created_at.desc(), User.full_name.asc())).all())


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        full_name=payload.full_name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        emp_id=payload.emp_id,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from None

    db.refresh(user)
    return user


def set_user_employee(db: Session, user_id: UUID, emp_id: str | None) -> User:
    """Link a user to an employee (or clear the link with None)."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    user.emp_id = emp_id
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session, user_id: UUID, payload: UserUpdate, acting_user: User
) -> User:
    """Edit a user: name, role, active flag, Employee ID, or reset the password.

    Two guards keep the system from locking itself out:
    - An admin cannot deactivate or change the role of their own account.
    - The last active admin cannot be deactivated or demoted.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    changes = payload.model_dump(exclude_unset=True)
    new_role = changes.get("role") or user.role
    new_active = changes.get("is_active")
    if new_active is None:
        new_active = user.is_active

    if user.id == acting_user.id:
        if not new_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can't deactivate your own account",
            )
        if new_role != user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You can't change your own role",
            )

    was_active_admin = user.role == UserRole.ADMIN and user.is_active
    stays_active_admin = new_role == UserRole.ADMIN and new_active
    if was_active_admin and not stays_active_admin:
        other_admins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
                User.id != user.id,
            )
        )
        if not other_admins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one active admin is required",
            )

    if changes.get("full_name") is not None:
        user.full_name = changes["full_name"]
    user.role = new_role
    user.is_active = new_active
    if "emp_id" in changes:
        user.emp_id = changes["emp_id"]
    if changes.get("password"):
        user.password_hash = hash_password(changes["password"])

    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    """Change the signed-in user's own password.

    A wrong current password is a 400, not a 401: the frontend treats any 401
    as an expired session and signs the person out.
    """
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if verify_password(new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )
    user.password_hash = hash_password(new_password)
    db.commit()


def authenticate_user(db: Session, email: str, password: str) -> Token:
    user = get_user_by_email(db=db, email=email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


def refresh_tokens(db: Session, refresh_token: str) -> Token:
    """Swap a valid refresh token for a new access token and a new refresh token.

    The user is looked up again, so a deactivated account stops renewing at once.
    Every failure is the same 401 and the frontend then asks for a login.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_refresh_token(refresh_token)
    if user_id is None:
        raise invalid
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise invalid
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )

