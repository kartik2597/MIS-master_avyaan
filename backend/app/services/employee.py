from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def get_employee_or_404(db: Session, employee_id: UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )
    return employee


def apply_employee_filters(
    statement: Select[tuple[Employee]],
    *,
    search: str | None = None,
    emp_id: str | None = None,
    employee_name: str | None = None,
    department: str | None = None,
    process: str | None = None,
    manager_name: str | None = None,
    tl_name: str | None = None,
) -> Select[tuple[Employee]]:
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                Employee.emp_id.ilike(pattern),
                Employee.employee_name.ilike(pattern),
            )
        )
    if emp_id:
        statement = statement.where(Employee.emp_id.ilike(f"%{emp_id}%"))
    if employee_name:
        statement = statement.where(Employee.employee_name.ilike(f"%{employee_name}%"))
    if department:
        statement = statement.where(Employee.department == department)
    if process:
        statement = statement.where(Employee.process == process)
    if manager_name:
        statement = statement.where(Employee.manager_name == manager_name)
    if tl_name:
        statement = statement.where(Employee.tl_name == tl_name)

    return statement


def list_employees(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    emp_id: str | None = None,
    employee_name: str | None = None,
    department: str | None = None,
    process: str | None = None,
    manager_name: str | None = None,
    tl_name: str | None = None,
) -> tuple[list[Employee], int]:
    filtered_statement = apply_employee_filters(
        select(Employee),
        search=search,
        emp_id=emp_id,
        employee_name=employee_name,
        department=department,
        process=process,
        manager_name=manager_name,
        tl_name=tl_name,
    )

    total = db.scalar(
        select(func.count()).select_from(filtered_statement.subquery())
    ) or 0
    employees = db.scalars(
        filtered_statement
        .order_by(Employee.employee_name.asc(), Employee.emp_id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return list(employees), total


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    employee = Employee(**payload.model_dump())
    db.add(employee)
    return commit_employee_change(db, employee)


def update_employee(db: Session, employee: Employee, payload: EmployeeUpdate) -> Employee:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    return commit_employee_change(db, employee)


def delete_employee(db: Session, employee: Employee) -> None:
    db.delete(employee)
    db.commit()


def commit_employee_change(db: Session, employee: Employee) -> Employee:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee with this emp_id already exists",
        ) from None

    db.refresh(employee)
    return employee

