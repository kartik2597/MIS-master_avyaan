from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
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
        search = search.strip()
    if search:
        # Escape LIKE wildcards so typing "%" or "_" searches for the character.
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(
                Employee.emp_id.ilike(pattern, escape="\\"),
                Employee.employee_name.ilike(pattern, escape="\\"),
                Employee.email.ilike(pattern, escape="\\"),
                Employee.mobile.ilike(pattern, escape="\\"),
                Employee.department.ilike(pattern, escape="\\"),
                Employee.process.ilike(pattern, escape="\\"),
                Employee.designation.ilike(pattern, escape="\\"),
                Employee.manager_name.ilike(pattern, escape="\\"),
                Employee.tl_name.ilike(pattern, escape="\\"),
                Employee.location.ilike(pattern, escape="\\"),
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
    old_emp_id = employee.emp_id
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(employee, field, value)

    new_emp_id = changes.get("emp_id")
    if new_emp_id and new_emp_id != old_emp_id:
        # Report tables keep emp_id as plain text (no foreign key), so move
        # their rows to the new ID in the same transaction.
        for model in (AgentDailyPerformance, AgentShiftAdherence, AgentShrinkage):
            db.execute(
                update(model)
                .where(model.emp_id == old_emp_id)
                .values(emp_id=new_emp_id)
            )
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
            detail="Employee ID already exists, or the new ID clashes with existing report rows",
        ) from None

    db.refresh(employee)
    return employee

