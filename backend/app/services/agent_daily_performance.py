from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_daily_performance import AgentDailyPerformance
from app.schemas.agent_daily_performance import (
    AgentDailyPerformanceCreate,
    AgentDailyPerformanceUpdate,
)


def create_agent_daily_performance(
    db: Session,
    payload: AgentDailyPerformanceCreate,
) -> AgentDailyPerformance:
    performance = AgentDailyPerformance(**payload.model_dump())
    db.add(performance)
    db.commit()
    db.refresh(performance)
    return performance


def get_agent_daily_performance(
    db: Session,
    performance_id: UUID,
) -> AgentDailyPerformance | None:
    return db.get(AgentDailyPerformance, performance_id)


def get_agent_daily_performance_or_404(
    db: Session,
    performance_id: UUID,
) -> AgentDailyPerformance:
    performance = get_agent_daily_performance(db=db, performance_id=performance_id)
    if performance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent daily performance record not found",
        )
    return performance


def list_agent_daily_performance(
    db: Session,
    *,
    emp_id: str | None = None,
    report_date=None,
    campaign: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AgentDailyPerformance]:
    statement = select(AgentDailyPerformance)
    if emp_id:
        statement = statement.where(AgentDailyPerformance.emp_id == emp_id)
    if report_date:
        statement = statement.where(AgentDailyPerformance.report_date == report_date)
    if campaign:
        statement = statement.where(AgentDailyPerformance.campaign == campaign)

    statement = (
        statement
        .order_by(
            AgentDailyPerformance.report_date.desc(),
            AgentDailyPerformance.emp_id.asc(),
        )
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def update_agent_daily_performance(
    db: Session,
    performance: AgentDailyPerformance,
    payload: AgentDailyPerformanceUpdate,
) -> AgentDailyPerformance:
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(performance, field_name, value)

    db.commit()
    db.refresh(performance)
    return performance


def delete_agent_daily_performance(
    db: Session,
    performance: AgentDailyPerformance,
) -> None:
    db.delete(performance)
    db.commit()


def bulk_create_agent_daily_performance(
    db: Session,
    payloads: Iterable[AgentDailyPerformanceCreate],
) -> list[AgentDailyPerformance]:
    records = [
        AgentDailyPerformance(**payload.model_dump())
        for payload in payloads
    ]
    if not records:
        return []

    db.add_all(records)
    db.commit()

    for record in records:
        db.refresh(record)

    return records

