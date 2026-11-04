"""Health checks, request IDs and the security headers added in app.main."""


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_the_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_security_headers_are_set(client):
    headers = client.get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cache-control"] == "no-store"
    assert "x-process-time-ms" in headers


def test_safe_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-abc_123"})
    assert response.headers["x-request-id"] == "trace-abc_123"


def test_unsafe_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "bad id with spaces!"})
    request_id = response.headers["x-request-id"]
    assert request_id != "bad id with spaces!"
    assert len(request_id) == 12


def test_request_id_is_generated_when_missing(client):
    assert client.get("/health").headers["x-request-id"]
