from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.models.employee import Employee
from app.models.user import UserRole
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeList,
    EmployeeRead,
    EmployeeUpdate,
)
from app.services.employee import (
    create_employee,
    delete_employee,
    get_employee_or_404,
    list_employees,
    update_employee,
)


router = APIRouter()

VIEW_ROLES = [UserRole.ADMIN, UserRole.MIS, UserRole.MANAGER, UserRole.TL]
WRITE_ROLES = [UserRole.ADMIN, UserRole.MIS]


@router.post(
    "",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def create_employee_record(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
) -> Employee:
    return create_employee(db=db, payload=payload)


@router.get(
    "",
    response_model=EmployeeList,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def read_employees(
    db: Session = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    emp_id: str | None = None,
    employee_name: str | None = None,
    department: str | None = None,
    process: str | None = None,
    manager_name: str | None = None,
    tl_name: str | None = None,
) -> EmployeeList:
    employees, total = list_employees(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        emp_id=emp_id,
        employee_name=employee_name,
        department=department,
        process=process,
        manager_name=manager_name,
        tl_name=tl_name,
    )
    return EmployeeList(items=employees, total=total, page=page, page_size=page_size)


@router.get(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[Depends(require_role(VIEW_ROLES))],
)
def read_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
) -> Employee:
    return get_employee_or_404(db=db, employee_id=employee_id)


@router.put(
    "/{employee_id}",
    response_model=EmployeeRead,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def update_employee_record(
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
) -> Employee:
    employee = get_employee_or_404(db=db, employee_id=employee_id)
    return update_employee(db=db, employee=employee, payload=payload)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(WRITE_ROLES))],
)
def delete_employee_record(
    employee_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    employee = get_employee_or_404(db=db, employee_id=employee_id)
    delete_employee(db=db, employee=employee)

