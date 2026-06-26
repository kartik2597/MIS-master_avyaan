from collections.abc import Iterable
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_shift_adherence import AgentShiftAdherence
from app.schemas.agent_shift_adherence import (
    AgentShiftAdherenceCreate,
    AgentShiftAdherenceUpdate,
)


def create_agent_shift_adherence(
    db: Session,
    payload: AgentShiftAdherenceCreate,
) -> AgentShiftAdherence:
    adherence = AgentShiftAdherence(**payload.model_dump())
    db.add(adherence)
    db.commit()
    db.refresh(adherence)
    return adherence


def get_agent_shift_adherence(
    db: Session,
    adherence_id: UUID,
) -> AgentShiftAdherence | None:
    return db.get(AgentShiftAdherence, adherence_id)


def get_agent_shift_adherence_or_404(
    db: Session,
    adherence_id: UUID,
) -> AgentShiftAdherence:
    adherence = get_agent_shift_adherence(db=db, adherence_id=adherence_id)
    if adherence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent shift adherence record not found",
        )
    return adherence


def get_agent_shift_adherence_by_business_key(
    db: Session,
    *,
    emp_id: str,
    report_date: date,
) -> AgentShiftAdherence | None:
    statement = select(AgentShiftAdherence).where(
        AgentShiftAdherence.emp_id == emp_id,
        AgentShiftAdherence.report_date == report_date,
    )
    return db.scalars(statement).first()


def list_agent_shift_adherence(
    db: Session,
    *,
    emp_id: str | None = None,
    report_date: date | None = None,
    manager_name: str | None = None,
    process: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AgentShiftAdherence]:
    statement = select(AgentShiftAdherence)
    if emp_id:
        statement = statement.where(AgentShiftAdherence.emp_id == emp_id)
    if report_date:
        statement = statement.where(AgentShiftAdherence.report_date == report_date)
    if manager_name:
        statement = statement.where(AgentShiftAdherence.manager_name == manager_name)
    if process:
        statement = statement.where(AgentShiftAdherence.process == process)

    statement = (
        statement
        .order_by(
            AgentShiftAdherence.report_date.desc(),
            AgentShiftAdherence.emp_id.asc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def update_agent_shift_adherence(
    db: Session,
    adherence: AgentShiftAdherence,
    payload: AgentShiftAdherenceUpdate,
) -> AgentShiftAdherence:
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(adherence, field_name, value)

    db.commit()
    db.refresh(adherence)
    return adherence


def delete_agent_shift_adherence(
    db: Session,
    adherence: AgentShiftAdherence,
) -> None:
    db.delete(adherence)
    db.commit()


def bulk_create_agent_shift_adherence(
    db: Session,
    payloads: Iterable[AgentShiftAdherenceCreate],
) -> list[AgentShiftAdherence]:
    records = [
        AgentShiftAdherence(**payload.model_dump())
        for payload in payloads
    ]
    if not records:
        return []

    db.add_all(records)
    db.commit()

    for record in records:
        db.refresh(record)

    return records
