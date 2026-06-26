from collections.abc import Callable, Sequence
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import get_db
from app.models.user import User, UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = UUID(subject)
    except (JWTError, ValueError):
        raise credentials_exception from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(allowed_roles: Sequence[UserRole | str]) -> Callable[[User], User]:
    normalized_roles = {
        role if isinstance(role, UserRole) else UserRole(role)
        for role in allowed_roles
    }

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return role_dependency

