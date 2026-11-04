from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import rate_limit
from app.auth.dependencies import get_current_user, require_role
from app.auth.service import (
    authenticate_user,
    change_password,
    create_user,
    list_users,
    refresh_tokens,
    set_user_employee,
    update_user,
)
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, Token
from app.schemas.user import UserCreate, UserEmployeeLink, UserRead, UserUpdate


router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Token:
    client_host = request.client.host if request.client else None
    rate_limit.ensure_not_locked(client_host, payload.email)
    try:
        token = authenticate_user(
            db=db, email=payload.email, password=payload.password
        )
    except HTTPException as exc:
        # Only wrong credentials count; an inactive account is not a guess.
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            rate_limit.record_failure(client_host, payload.email)
        raise
    rate_limit.clear_failures(client_host, payload.email)
    return token


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> Token:
    return refresh_tokens(db=db, refresh_token=payload.refresh_token)


@router.post(
    "/create-user",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def create_new_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return create_user(db=db, payload=payload)


@router.get(
    "/users",
    response_model=list[UserRead],
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def read_users(db: Session = Depends(get_db)) -> list[User]:
    return list_users(db=db)


@router.patch("/users/{user_id}", response_model=UserRead)
def edit_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role([UserRole.ADMIN])),
) -> User:
    return update_user(db=db, user_id=user_id, payload=payload, acting_user=admin)


@router.put(
    "/users/{user_id}/employee",
    response_model=UserRead,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def link_user_to_employee(
    user_id: UUID,
    payload: UserEmployeeLink,
    db: Session = Depends(get_db),
) -> User:
    return set_user_employee(db=db, user_id=user_id, emp_id=payload.emp_id)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_own_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    change_password(
        db=db,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )

