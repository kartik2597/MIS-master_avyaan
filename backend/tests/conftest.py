"""Shared fixtures for the API tests.

The app talks to PostgreSQL, but the tests run against an in-memory SQLite
database so they need no running server. Only the JSONB column type needs a
helper, because SQLite has no JSONB: it is created as plain JSON instead.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.auth import rate_limit
from app.auth.security import hash_password
from app.core.config import settings
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.user import User, UserRole

DEFAULT_PASSWORD = "Password123"


@compiles(JSONB, "sqlite")
def _render_jsonb_as_json_on_sqlite(type_, compiler, **kwargs):
    return "JSON"


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    rate_limit.reset_all()
    yield
    rate_limit.reset_all()


@pytest.fixture()
def engine():
    # StaticPool keeps one shared in-memory database across the test client's
    # worker threads.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def client(engine, tmp_path, monkeypatch):
    # Uploaded files go to a throwaway folder, never the real storage folder.
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(engine):
    def factory(
        *,
        role: UserRole = UserRole.ADMIN,
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
        is_active: bool = True,
        emp_id: str | None = None,
    ) -> User:
        with Session(engine) as session:
            user = User(
                full_name="Test User",
                email=email or f"{role.value.lower()}@mismaster.com",
                password_hash=hash_password(password),
                role=role,
                is_active=is_active,
                emp_id=emp_id,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    return factory


@pytest.fixture()
def auth_headers(client, make_user):
    """Create a user with the given role, log in, and return the auth header."""

    def factory(
        role: UserRole = UserRole.ADMIN,
        *,
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
    ) -> dict[str, str]:
        email = email or f"{role.value.lower()}@mismaster.com"
        make_user(role=role, email=email, password=password)
        response = client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return factory
