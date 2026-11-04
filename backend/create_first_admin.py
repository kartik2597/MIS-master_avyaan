"""Create the first ADMIN account.

Run from the backend folder:  python create_first_admin.py
"""
from getpass import getpass

from app.auth.service import create_user
from app.database.session import SessionLocal
from app.models.user import UserRole
from app.schemas.user import UserCreate


def prompt_required(label: str) -> str:
    value = input(f"{label}: ").strip()
    if not value:
        raise SystemExit(f"{label} is required.")
    return value


def main() -> None:
    name = prompt_required("Full name")
    email = prompt_required("Email")
    password = getpass("Enter a NEW password: ")
    if getpass("Confirm password: ") != password:
        raise SystemExit("Passwords do not match.")

    db = SessionLocal()
    try:
        payload = UserCreate(
            full_name=name,
            email=email,
            password=password,
            role=UserRole.ADMIN,
            is_active=True,
        )

        user = create_user(db=db, payload=payload)

        print("\nADMIN ACCOUNT CREATED SUCCESSFULLY!")
        print("Name:", user.full_name)
        print("Email:", user.email)
        print("Role:", user.role.value)
    finally:
        db.close()


if __name__ == "__main__":
    main()
