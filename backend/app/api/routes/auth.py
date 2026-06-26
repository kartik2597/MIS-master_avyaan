from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.service import authenticate_user, create_user
from app.database.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserRead


router = APIRouter()


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    return authenticate_user(db=db, email=payload.email, password=payload.password)


@router.post(
    "/create-user",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role([UserRole.ADMIN]))],
)
def create_new_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    return create_user(db=db, payload=payload)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user

