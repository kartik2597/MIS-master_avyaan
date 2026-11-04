"""Login, token checks and role rules, through the real API routes."""

from app.models.user import UserRole

PASSWORD = "Password123"


def test_login_returns_a_bearer_token(client, make_user):
    make_user(role=UserRole.ADMIN, email="admin@mismaster.com")

    response = client.post(
        "/auth/login", json={"email": "admin@mismaster.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_with_wrong_password_is_rejected(client, make_user):
    make_user(email="admin@mismaster.com")

    response = client.post(
        "/auth/login", json={"email": "admin@mismaster.com", "password": "WrongPass999"}
    )

    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(client):
    response = client.post(
        "/auth/login", json={"email": "nobody@mismaster.com", "password": PASSWORD}
    )

    assert response.status_code == 401


def test_repeated_wrong_passwords_lock_the_login(client, make_user):
    from app.auth.rate_limit import MAX_FAILURES

    make_user(email="locked@mismaster.com")
    wrong = {"email": "locked@mismaster.com", "password": "WrongPass999"}

    for _ in range(MAX_FAILURES):
        assert client.post("/auth/login", json=wrong).status_code == 401

    locked = client.post("/auth/login", json=wrong)
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers

    # Even the correct password is refused while locked.
    right = {"email": "locked@mismaster.com", "password": PASSWORD}
    assert client.post("/auth/login", json=right).status_code == 429


def test_successful_login_clears_failed_attempts(client, make_user):
    from app.auth.rate_limit import MAX_FAILURES

    make_user(email="ok@mismaster.com")
    wrong = {"email": "ok@mismaster.com", "password": "WrongPass999"}
    right = {"email": "ok@mismaster.com", "password": PASSWORD}

    for _ in range(MAX_FAILURES - 1):
        assert client.post("/auth/login", json=wrong).status_code == 401
    assert client.post("/auth/login", json=right).status_code == 200

    # The count started over, so one more miss is just a 401.
    assert client.post("/auth/login", json=wrong).status_code == 401


def test_inactive_user_cannot_log_in(client, make_user):
    make_user(email="off@mismaster.com", is_active=False)

    response = client.post(
        "/auth/login", json={"email": "off@mismaster.com", "password": PASSWORD}
    )

    assert response.status_code == 403


def test_me_requires_a_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401


def test_me_returns_the_logged_in_user(client, auth_headers):
    headers = auth_headers(UserRole.MIS, email="mis@mismaster.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "mis@mismaster.com"
    assert response.json()["role"] == "MIS"


def test_only_admin_can_create_users(client, auth_headers):
    payload = {
        "full_name": "New Person",
        "email": "new@mismaster.com",
        "password": PASSWORD,
        "role": "TL",
    }

    mis_headers = auth_headers(UserRole.MIS)
    assert client.post("/auth/create-user", json=payload, headers=mis_headers).status_code == 403

    admin_headers = auth_headers(UserRole.ADMIN)
    created = client.post("/auth/create-user", json=payload, headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["role"] == "TL"

    duplicate = client.post("/auth/create-user", json=payload, headers=admin_headers)
    assert duplicate.status_code == 409


def test_deactivated_user_token_stops_working(client, auth_headers, engine):
    from sqlalchemy.orm import Session

    from app.models.user import User

    headers = auth_headers(UserRole.ADMIN, email="gone@mismaster.com")
    assert client.get("/auth/me", headers=headers).status_code == 200

    with Session(engine) as session:
        user = session.query(User).filter_by(email="gone@mismaster.com").one()
        user.is_active = False
        session.commit()

    assert client.get("/auth/me", headers=headers).status_code == 401


def _login_tokens(client, make_user, email="refresh@mismaster.com", **user_kwargs):
    make_user(email=email, **user_kwargs)
    response = client.post(
        "/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200
    return response.json()


def test_login_returns_a_refresh_token(client, make_user):
    tokens = _login_tokens(client, make_user)

    assert tokens["refresh_token"]
    assert tokens["refresh_token"] != tokens["access_token"]


def test_refresh_returns_working_tokens(client, make_user):
    tokens = _login_tokens(client, make_user)

    response = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 200
    renewed = response.json()
    assert renewed["refresh_token"]
    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {renewed['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "refresh@mismaster.com"


def test_access_token_cannot_be_used_to_refresh(client, make_user):
    tokens = _login_tokens(client, make_user)

    response = client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )

    assert response.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client, make_user):
    tokens = _login_tokens(client, make_user)

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )

    assert response.status_code == 401


def test_refresh_rejects_a_garbage_token(client):
    response = client.post("/auth/refresh", json={"refresh_token": "not-a-token"})

    assert response.status_code == 401


def test_refresh_stops_working_for_a_deactivated_user(client, make_user, engine):
    from sqlalchemy.orm import Session

    from app.models.user import User

    tokens = _login_tokens(client, make_user, email="off2@mismaster.com")
    with Session(engine) as session:
        user = session.query(User).filter_by(email="off2@mismaster.com").one()
        user.is_active = False
        session.commit()

    response = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )

    assert response.status_code == 401
