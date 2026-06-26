from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.schemas.dashboard import DashboardKpis


ZERO_DECIMAL = Decimal("0")


def _decimal(value: object) -> Decimal:
    if value is None:
        return ZERO_DECIMAL
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def get_dashboard_kpis(db: Session) -> DashboardKpis:
    performance_totals = db.execute(
        select(
            func.coalesce(func.sum(AgentDailyPerformance.talk_time), 0),
            func.coalesce(func.sum(AgentDailyPerformance.login_hours), 0),
            func.coalesce(func.sum(AgentDailyPerformance.staff_time), 0),
            func.coalesce(func.sum(AgentDailyPerformance.idle_time), 0),
            func.coalesce(func.sum(AgentDailyPerformance.break_time), 0),
        )
    ).one()

    adherence_totals = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.late_login_minutes > 0, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.early_logout_minutes > 0, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.adherence_flag.is_(True), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (AgentShiftAdherence.non_adherence_flag.is_(True), 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(func.sum(AgentShiftAdherence.downtime_seconds), 0),
        )
    ).one()

    shrinkage_totals = db.execute(
        select(
            func.coalesce(func.sum(AgentShrinkage.agent_count), 0),
            func.coalesce(func.sum(AgentShrinkage.present_count), 0),
            func.coalesce(func.sum(AgentShrinkage.planned_shrinkage), 0),
            func.coalesce(func.sum(AgentShrinkage.unplanned_shrinkage), 0),
            func.coalesce(func.sum(AgentShrinkage.attrition), 0),
        )
    ).one()

    planned_shrinkage = _decimal(shrinkage_totals[2])
    unplanned_shrinkage = _decimal(shrinkage_totals[3])

    return DashboardKpis(
        head_count=_int(shrinkage_totals[0]),
        present_count=_int(shrinkage_totals[1]),
        late_login_count=_int(adherence_totals[0]),
        early_logout_count=_int(adherence_totals[1]),
        shift_adherence_count=_int(adherence_totals[2]),
        non_adherence_count=_int(adherence_totals[3]),
        planned_shrinkage=planned_shrinkage,
        unplanned_shrinkage=unplanned_shrinkage,
        overall_shrinkage=planned_shrinkage + unplanned_shrinkage,
        attrition_count=_int(shrinkage_totals[4]),
        total_talk_time=_decimal(performance_totals[0]),
        total_login_time=_decimal(performance_totals[1]),
        total_staff_time=_decimal(performance_totals[2]),
        total_downtime=_decimal(adherence_totals[4]),
        total_idle_time=_decimal(performance_totals[3]),
        total_break_time=_decimal(performance_totals[4]),
    )
