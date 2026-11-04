"""Upload endpoint, import endpoint and dashboard route, through the real API."""

import io

import pytest

pytest.importorskip("pandas")

from app.models.user import UserRole

MASTER_HEADER = (
    "Employee ID,Employee Name,Email,Mobile,Department,Process,Designation,"
    "Manager Name,TL Name,Date Of Joining,Employment Status,Location"
)
MASTER_ROW = "E100,Asha Rao,asha@example.com,9876543210,Ops,Sales,Agent,Ravi,Meera,2025-04-01,Active,Pune"
MASTER_ROW_BLANK_MOBILE = "E101,Bela Nair,bela@example.com,,Ops,Sales,Agent,Ravi,Meera,2025-04-01,Active,Pune"


def csv_file(text: str, name: str = "report.csv"):
    return {"file": (name, io.BytesIO(text.encode("utf-8")), "text/csv")}


def upload(client, headers, text: str, name: str = "report.csv"):
    return client.post("/uploads/file", files=csv_file(text, name), headers=headers)


# --- Upload endpoint -------------------------------------------------------


def test_upload_requires_login(client):
    response = client.post("/uploads/file", files=csv_file(MASTER_HEADER))

    assert response.status_code == 401


def test_upload_rejects_unsupported_extension(client, auth_headers):
    response = upload(client, auth_headers(), "hello", name="notes.txt")

    assert response.status_code == 400


def test_full_master_database_file_is_validated(client, auth_headers):
    response = upload(client, auth_headers(), f"{MASTER_HEADER}\n{MASTER_ROW}\n")

    assert response.status_code == 201
    body = response.json()
    assert body["detected_report_type"] == "MASTER_DATABASE"
    assert body["missing_columns"] == []

    record = client.get(f"/uploads/{body['upload_id']}", headers=auth_headers())
    assert record.json()["upload_status"] == "VALIDATED"
    assert record.json()["total_records"] == 1


def test_three_column_master_file_is_not_validated(client, auth_headers):
    # Upload and import must agree: a file that cannot be imported is never
    # marked VALIDATED.
    headers = auth_headers()
    text = "Employee ID,Employee Name,Email\nE100,Asha Rao,asha@example.com\n"

    response = upload(client, headers, text)

    assert response.status_code == 201
    upload_id = response.json()["upload_id"]
    record = client.get(f"/uploads/{upload_id}", headers=headers).json()
    assert record["upload_status"] == "FAILED"

    imported = client.post(f"/imports/master-database/{upload_id}", headers=headers)
    assert imported.status_code == 400


def test_upload_history_lists_the_upload(client, auth_headers):
    headers = auth_headers()
    upload(client, headers, f"{MASTER_HEADER}\n{MASTER_ROW}\n")

    response = client.get("/uploads", headers=headers)

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_only_admin_or_mis_can_delete_an_upload(client, auth_headers):
    admin_headers = auth_headers(UserRole.ADMIN)
    upload_id = upload(
        client, admin_headers, f"{MASTER_HEADER}\n{MASTER_ROW}\n"
    ).json()["upload_id"]

    tl_headers = auth_headers(UserRole.TL)
    assert client.delete(f"/uploads/{upload_id}", headers=tl_headers).status_code == 403
    assert client.delete(f"/uploads/{upload_id}", headers=admin_headers).status_code == 204


# --- Import endpoint -------------------------------------------------------


def test_import_creates_employees_and_reports_failed_rows(client, auth_headers):
    headers = auth_headers()
    text = f"{MASTER_HEADER}\n{MASTER_ROW}\n{MASTER_ROW_BLANK_MOBILE}\n"
    upload_id = upload(client, headers, text).json()["upload_id"]

    response = client.post(f"/imports/master-database/{upload_id}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_records"] == 2
    assert body["processed_records"] == 1
    assert body["failed_records"] == 1
    # The response itself explains which row was skipped and why.
    assert "row 3" in body["message"]
    assert "mobile" in body["message"]
    record = client.get(f"/uploads/{upload_id}", headers=headers).json()
    assert record["upload_status"] == "COMPLETED"
    # The skipped row is explained, not just counted.
    assert "row 3" in record["error_message"]
    assert "mobile" in record["error_message"]


def test_completed_import_cannot_be_run_twice(client, auth_headers):
    headers = auth_headers()
    upload_id = upload(
        client, headers, f"{MASTER_HEADER}\n{MASTER_ROW}\n"
    ).json()["upload_id"]
    assert client.post(f"/imports/master-database/{upload_id}", headers=headers).status_code == 200

    again = client.post(f"/imports/master-database/{upload_id}", headers=headers)

    assert again.status_code == 400


def test_failed_import_can_be_retried(client, auth_headers, engine):
    from sqlalchemy.orm import Session

    from app.models.upload_history import UploadHistory

    headers = auth_headers()
    upload_id = upload(
        client, headers, f"{MASTER_HEADER}\n{MASTER_ROW}\n"
    ).json()["upload_id"]

    # Simulate an import that failed part-way: status FAILED, file still valid.
    with Session(engine) as session:
        record = session.query(UploadHistory).one()
        record.upload_status = "FAILED"
        session.commit()

    retry = client.post(f"/imports/master-database/{upload_id}", headers=headers)

    assert retry.status_code == 200
    assert retry.json()["processed_records"] == 1


def test_import_requires_admin_or_mis(client, auth_headers):
    admin_headers = auth_headers(UserRole.ADMIN)
    upload_id = upload(
        client, admin_headers, f"{MASTER_HEADER}\n{MASTER_ROW}\n"
    ).json()["upload_id"]

    response = client.post(
        f"/imports/master-database/{upload_id}", headers=auth_headers(UserRole.TL)
    )

    assert response.status_code == 403


def test_import_of_unknown_upload_is_404(client, auth_headers):
    response = client.post(
        "/imports/master-database/00000000-0000-0000-0000-000000000000",
        headers=auth_headers(),
    )

    assert response.status_code == 404


# --- Dashboard route -------------------------------------------------------


def test_dashboard_requires_login(client):
    assert client.get("/dashboard/kpis").status_code == 401


def test_dashboard_with_no_data_returns_zeros(client, auth_headers):
    response = client.get("/dashboard/kpis", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["report_date"] is None
    assert float(response.json()["total_staff_time"]) == 0


def test_dashboard_rejects_reversed_dates(client, auth_headers):
    response = client.get(
        "/dashboard/kpis",
        params={"date_from": "2026-11-02", "date_to": "2026-11-01"},
        headers=auth_headers(),
    )

    assert response.status_code == 400
