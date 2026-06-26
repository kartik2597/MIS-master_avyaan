from collections.abc import Iterable
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_shrinkage import AgentShrinkage
from app.schemas.agent_shrinkage import AgentShrinkageCreate, AgentShrinkageUpdate


def create_agent_shrinkage(
    db: Session,
    payload: AgentShrinkageCreate,
) -> AgentShrinkage:
    shrinkage = AgentShrinkage(**payload.model_dump())
    db.add(shrinkage)
    db.commit()
    db.refresh(shrinkage)
    return shrinkage


def get_agent_shrinkage(
    db: Session,
    shrinkage_id: UUID,
) -> AgentShrinkage | None:
    return db.get(AgentShrinkage, shrinkage_id)


def get_agent_shrinkage_or_404(
    db: Session,
    shrinkage_id: UUID,
) -> AgentShrinkage:
    shrinkage = get_agent_shrinkage(db=db, shrinkage_id=shrinkage_id)
    if shrinkage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent shrinkage record not found",
        )
    return shrinkage


def get_agent_shrinkage_by_business_key(
    db: Session,
    *,
    emp_id: str,
    report_date: date,
) -> AgentShrinkage | None:
    statement = select(AgentShrinkage).where(
        AgentShrinkage.emp_id == emp_id,
        AgentShrinkage.report_date == report_date,
    )
    return db.scalars(statement).first()


def list_agent_shrinkage(
    db: Session,
    *,
    emp_id: str | None = None,
    report_date: date | None = None,
    manager_name: str | None = None,
    process: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AgentShrinkage]:
    statement = select(AgentShrinkage)
    if emp_id:
        statement = statement.where(AgentShrinkage.emp_id == emp_id)
    if report_date:
        statement = statement.where(AgentShrinkage.report_date == report_date)
    if manager_name:
        statement = statement.where(AgentShrinkage.manager_name == manager_name)
    if process:
        statement = statement.where(AgentShrinkage.process == process)

    statement = (
        statement
        .order_by(
            AgentShrinkage.report_date.desc(),
            AgentShrinkage.emp_id.asc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def update_agent_shrinkage(
    db: Session,
    shrinkage: AgentShrinkage,
    payload: AgentShrinkageUpdate,
) -> AgentShrinkage:
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(shrinkage, field_name, value)

    db.commit()
    db.refresh(shrinkage)
    return shrinkage


def delete_agent_shrinkage(
    db: Session,
    shrinkage: AgentShrinkage,
) -> None:
    db.delete(shrinkage)
    db.commit()


def bulk_create_agent_shrinkage(
    db: Session,
    payloads: Iterable[AgentShrinkageCreate],
) -> list[AgentShrinkage]:
    records = [
        AgentShrinkage(**payload.model_dump())
        for payload in payloads
    ]
    if not records:
        return []

    db.add_all(records)
    db.commit()

    for record in records:
        db.refresh(record)

    return records
