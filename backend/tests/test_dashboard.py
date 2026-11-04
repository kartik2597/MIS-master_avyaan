"""Dashboard KPI calculations, run against an in-memory SQLite database."""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models.agent_daily_performance import AgentDailyPerformance
from app.models.agent_shift_adherence import AgentShiftAdherence
from app.models.agent_shrinkage import AgentShrinkage
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.services.dashboard import (
    apply_dashboard_filters,
    get_dashboard_agents,
    get_dashboard_attendance,
    get_dashboard_filter_options,
    get_dashboard_kpis,
    get_dashboard_scope,
    get_dashboard_trends,
)

HOUR = 3600
NOV_1 = date(2026, 11, 1)
NOV_2 = date(2026, 11, 2)

TABLES = [
    AgentDailyPerformance.__table__,
    AgentShiftAdherence.__table__,
    AgentShrinkage.__table__,
    Employee.__table__,
]


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=TABLES)
    with Session(engine) as session:
        yield session
    engine.dispose()


def performance(
    emp_id, day, *, staff=0, talk=0, idle=0, brk=0, campaign="Sales", attendance="P"
):
    return AgentDailyPerformance(
        emp_id=emp_id,
        employee_name=f"Agent {emp_id}",
        report_date=day,
        campaign=campaign,
        user_group="Tier1",
        attendance=attendance,
        # Same as the APR parser: APR has no login column, so it stores 0.
        login_hours=0,
        staff_time=staff,
        talk_time=talk,
        break_time=brk,
        idle_time=idle,
        productivity_percent=Decimal("87.50"),
        total_calls=0,
        dialer_total_calls=0,
        dialflow_total_calls=0,
        connected_calls=0,
        not_connected_calls=0,
        positive_calls=0,
        conversion_percent=0,
        tl_remark="",
    )


def adherence(
    emp_id,
    day,
    *,
    login=0,
    downtime=0,
    late=0,
    early=0,
    adhered=True,
):
    return AgentShiftAdherence(
        emp_id=emp_id,
        employee_name=f"Agent {emp_id}",
        report_date=day,
        status="Active",
        process="Sales",
        designation="Agent",
        manager_name="Manager",
        attendance="P",
        shift_start_time=time(9, 0),
        shift_end_time=time(18, 0),
        actual_login_time=time(9, 5),
        actual_logout_time=time(18, 0),
        login_hours_seconds=login,
        downtime_seconds=downtime,
        login_plus_downtime_seconds=login + downtime,
        shift_login_adherence_percent=Decimal("90.00"),
        adherence_status="Adhere" if adhered else "Non Adhere",
        late_login_minutes=late,
        early_logout_minutes=early,
        adherence_flag=adhered,
        non_adherence_flag=not adhered,
        non_adherence_percent=Decimal("0.00"),
    )


def shrinkage(
    emp_id,
    day,
    *,
    agents=1,
    present=1,
    planned="0",
    unplanned="0",
    attrition=0,
):
    return AgentShrinkage(
        emp_id=emp_id,
        employee_name=f"Agent {emp_id}",
        report_date=day,
        status="Active",
        process="Sales",
        designation="Agent",
        manager_name="Manager",
        date_of_joining=date(2025, 1, 1),
        login_hours_seconds=0,
        attendance="P",
        employee_age_days=300,
        tenure_bucket="180+",
        agent_count=agents,
        present_count=present,
        absent_count=0,
        lwp_count=0,
        cl_count=0,
        half_day_count=0,
        training_count=0,
        planned_shrinkage=Decimal(planned),
        unplanned_shrinkage=Decimal(unplanned),
        opening_headcount=0,
        closing_headcount=0,
        attrition=attrition,
    )


def test_empty_database_gives_zeros(db):
    kpis = get_dashboard_kpis(db)

    assert kpis.report_date is None
    assert kpis.head_count == 0
    assert kpis.total_staff_time == Decimal("0")
    assert kpis.total_login_time == Decimal("0")
    assert kpis.overall_shrinkage == Decimal("0")


def test_times_are_reported_in_hours(db):
    db.add_all(
        [
            performance("E1", NOV_1, staff=8 * HOUR, talk=3 * HOUR, idle=HOUR, brk=HOUR),
            performance("E2", NOV_1, staff=4 * HOUR + 1800, talk=HOUR, idle=0, brk=1800),
            adherence("E1", NOV_1, login=7 * HOUR, downtime=1800),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db)

    assert kpis.total_staff_time == Decimal("12.50")
    assert kpis.total_talk_time == Decimal("4.00")
    assert kpis.total_idle_time == Decimal("1.00")
    assert kpis.total_break_time == Decimal("1.50")
    assert kpis.total_downtime == Decimal("0.50")


def test_login_time_is_not_a_copy_of_staff_time(db):
    # APR copies staff time into its login column, so the login card must come
    # from the shift adherence report's "Login hours" instead.
    db.add_all(
        [
            performance("E1", NOV_1, staff=8 * HOUR),
            adherence("E1", NOV_1, login=7 * HOUR + 1800),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db)

    assert kpis.total_staff_time == Decimal("8.00")
    assert kpis.total_login_time == Decimal("7.50")


def test_cards_use_one_shared_day_when_no_dates_given(db):
    # APR and adherence have Nov 1 and Nov 2; shrinkage was only uploaded for
    # Nov 1. Every card must describe Nov 1, not each table's own latest day.
    db.add_all(
        [
            performance("E1", NOV_1, staff=1 * HOUR),
            performance("E1", NOV_2, staff=10 * HOUR),
            adherence("E1", NOV_1, login=2 * HOUR, late=5),
            adherence("E1", NOV_2, login=20 * HOUR, late=5),
            shrinkage("E1", NOV_1, agents=10, present=8, attrition=1),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db)

    assert kpis.report_date == NOV_1
    assert kpis.total_staff_time == Decimal("1.00")
    assert kpis.total_login_time == Decimal("2.00")
    assert kpis.late_login_count == 1
    assert kpis.head_count == 10
    assert kpis.present_count == 8
    assert kpis.attrition_count == 1


def test_tables_with_no_common_day_still_describe_a_single_day(db):
    db.add_all(
        [
            performance("E1", NOV_2, staff=3 * HOUR),
            adherence("E1", NOV_1, login=5 * HOUR, late=9),
            shrinkage("E1", NOV_1, agents=10, present=8),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db)

    # The newest day wins; reports with nothing on it show zeros, not Nov 1.
    assert kpis.report_date == NOV_2
    assert kpis.total_staff_time == Decimal("3.00")
    assert kpis.total_login_time == Decimal("0.00")
    assert kpis.late_login_count == 0
    assert kpis.head_count == 0


def test_explicit_range_sums_days_and_averages_head_count(db):
    db.add_all(
        [
            performance("E1", NOV_1, staff=2 * HOUR),
            performance("E1", NOV_2, staff=3 * HOUR),
            shrinkage("E1", NOV_1, agents=10, present=8, planned="10", attrition=1),
            shrinkage("E1", NOV_2, agents=20, present=12, planned="20", attrition=2),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db, date_from=NOV_1, date_to=NOV_2)

    assert kpis.report_date is None
    assert kpis.total_staff_time == Decimal("5.00")
    assert kpis.head_count == 15  # average of 10 and 20 per day
    assert kpis.present_count == 10
    assert kpis.attrition_count == 3
    assert kpis.planned_shrinkage == Decimal("15.00")  # averaged, not summed


def test_range_can_be_open_ended(db):
    db.add_all(
        [
            performance("E1", NOV_1, staff=2 * HOUR),
            performance("E1", NOV_2, staff=3 * HOUR),
        ]
    )
    db.commit()

    assert get_dashboard_kpis(db, date_from=NOV_2).total_staff_time == Decimal("3.00")
    assert get_dashboard_kpis(db, date_to=NOV_1).total_staff_time == Decimal("2.00")


def test_shrinkage_is_averaged_and_overall_is_planned_plus_unplanned(db):
    db.add_all(
        [
            shrinkage("E1", NOV_1, planned="10.00", unplanned="4.00"),
            shrinkage("E2", NOV_1, planned="20.00", unplanned="6.00"),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db)

    assert kpis.planned_shrinkage == Decimal("15.00")
    assert kpis.unplanned_shrinkage == Decimal("5.00")
    assert kpis.overall_shrinkage == Decimal("20.00")


def test_adherence_counts(db):
    db.add_all(
        [
            adherence("E1", NOV_1, late=10, adhered=False),
            adherence("E2", NOV_1, early=5, adhered=True),
            adherence("E3", NOV_1, adhered=True),
        ]
    )
    db.commit()

    kpis = get_dashboard_kpis(db)

    assert kpis.late_login_count == 1
    assert kpis.early_logout_count == 1
    assert kpis.shift_adherence_count == 2
    assert kpis.non_adherence_count == 1


def test_missing_reports_are_listed_so_zeros_are_not_mistaken_for_data(db):
    # Only APR was imported: the adherence and shrinkage cards have no data.
    db.add(performance("E1", NOV_2, staff=3 * HOUR))
    db.commit()

    kpis = get_dashboard_kpis(db)

    assert kpis.total_staff_time == Decimal("3.00")
    assert kpis.missing_reports == ["SHIFT_ADHERENCE", "SHRINKAGE"]


def test_no_missing_reports_when_all_three_are_imported(db):
    db.add_all(
        [
            performance("E1", NOV_1, staff=HOUR),
            adherence("E1", NOV_1, login=HOUR),
            shrinkage("E1", NOV_1, agents=1, present=1),
        ]
    )
    db.commit()

    assert get_dashboard_kpis(db).missing_reports == []


# --- Trends, attendance breakdown, agent table ---------------------------------


def test_trends_give_one_point_per_day_in_date_order(db):
    db.add_all(
        [
            shrinkage("E1", NOV_2, agents=10, present=7, planned="5", unplanned="3"),
            shrinkage("E1", NOV_1, agents=10, present=9, planned="2", unplanned="1"),
            adherence("E1", NOV_1, adhered=True),
            adherence("E2", NOV_1, adhered=False),
            performance("E1", NOV_1, staff=4 * HOUR, talk=2 * HOUR),
        ]
    )
    db.commit()

    points = get_dashboard_trends(db).points

    assert [point.report_date for point in points] == [NOV_1, NOV_2]
    first, second = points
    assert (first.head_count, first.present_count) == (10, 9)
    assert first.overall_shrinkage == 3.0
    assert first.adherence_percent == 50.0
    assert first.talk_time == 2.0
    assert first.staff_time == 4.0
    # Nov 2 has no adherence or activity rows: a gap, not a fake 0%.
    assert second.adherence_percent is None
    assert second.talk_time == 0.0
    assert second.overall_shrinkage == 8.0


def test_trends_fall_back_to_activity_when_shrinkage_is_missing(db):
    db.add_all(
        [
            performance("E1", NOV_1, attendance="Present"),
            performance("E2", NOV_1, attendance="Absent"),
            performance("E3", NOV_1, attendance="Leave"),
        ]
    )
    db.commit()

    (point,) = get_dashboard_trends(db).points

    assert point.head_count == 3
    assert point.present_count == 1
    assert point.overall_shrinkage is None


def test_trends_respect_an_explicit_range(db):
    db.add_all(
        [
            shrinkage("E1", NOV_1, agents=10, present=9),
            shrinkage("E1", NOV_2, agents=20, present=18),
        ]
    )
    db.commit()

    points = get_dashboard_trends(db, date_from=NOV_2, date_to=NOV_2).points

    assert [point.report_date for point in points] == [NOV_2]


def test_trends_are_empty_without_data(db):
    assert get_dashboard_trends(db).points == []


def test_attendance_breakdown_groups_status_spellings(db):
    db.add_all(
        [
            performance("E1", NOV_1, attendance="Present"),
            performance("E2", NOV_1, attendance="P"),
            performance("E3", NOV_1, attendance="Absent"),
            performance("E4", NOV_1, attendance="Leave"),
            performance("E5", NOV_1, attendance="CL"),
            performance("E6", NOV_1, attendance="something odd"),
        ]
    )
    db.commit()

    breakdown = get_dashboard_attendance(db)

    assert breakdown.report_date == NOV_1
    assert breakdown.total == 6
    assert {item.status: item.count for item in breakdown.slices} == {
        "Present": 2,
        "Absent": 1,
        "Leave": 2,
        "Other": 1,
    }
    # Fixed display order, empty groups left out.
    assert [item.status for item in breakdown.slices] == [
        "Present",
        "Absent",
        "Leave",
        "Other",
    ]


def test_attendance_breakdown_is_empty_without_data(db):
    breakdown = get_dashboard_attendance(db)

    assert breakdown.slices == []
    assert breakdown.total == 0


def test_agent_table_rolls_up_each_agent_over_a_range(db):
    db.add_all(
        [
            performance("E1", NOV_1, talk=2 * HOUR, idle=HOUR, brk=1800, attendance="Present"),
            performance("E1", NOV_2, talk=3 * HOUR, idle=0, brk=1800, attendance="Absent"),
            performance("E2", NOV_1, talk=HOUR, attendance="Present"),
            adherence("E1", NOV_1, login=8 * HOUR, late=10, adhered=False),
            adherence("E1", NOV_2, login=4 * HOUR, early=5, adhered=True),
        ]
    )
    db.commit()

    result = get_dashboard_agents(db, date_from=NOV_1, date_to=NOV_2)

    assert result.total == 2
    first, second = result.items
    assert (first.emp_id, second.emp_id) == ("E1", "E2")
    assert first.days_recorded == 2
    assert first.days_present == 1
    assert first.talk_time == 5.0
    assert first.idle_time == 1.0
    assert first.break_time == 1.0
    assert first.login_hours == 12.0
    assert first.late_logins == 1
    assert first.early_logouts == 1
    assert first.adherent_days == 1
    # E2 has no adherence rows: zeros, not an error.
    assert second.login_hours == 0.0
    assert second.late_logins == 0


def test_agent_table_search_matches_id_or_name_case_insensitively(db):
    db.add_all(
        [
            performance("EMP001", NOV_1),
            performance("EMP002", NOV_1),
            performance("XYZ900", NOV_1),
        ]
    )
    db.commit()

    by_id = get_dashboard_agents(db, search="emp00")
    by_name = get_dashboard_agents(db, search="agent xyz")

    assert by_id.total == 2
    assert {row.emp_id for row in by_id.items} == {"EMP001", "EMP002"}
    assert [row.emp_id for row in by_name.items] == ["XYZ900"]
    assert get_dashboard_agents(db, search="nobody").items == []


def test_agent_table_paginates(db):
    db.add_all([performance(f"E{n:02d}", NOV_1) for n in range(1, 6)])
    db.commit()

    page_two = get_dashboard_agents(db, page=2, page_size=2)

    assert page_two.total == 5
    assert [row.emp_id for row in page_two.items] == ["E03", "E04"]


# --- Role scoping ---------------------------------------------------------------


def employee(emp_id, name, *, manager="", tl=""):
    return Employee(
        emp_id=emp_id,
        employee_name=name,
        email=f"{emp_id.lower()}@example.com",
        mobile="9999999999",
        department="Ops",
        process="Sales",
        designation="Agent",
        manager_name=manager,
        tl_name=tl,
        date_of_joining=date(2025, 1, 1),
        employment_status="Active",
        location="Bhopal",
    )


def seed_team(session):
    """Manager M1 (Meera Shah) has A1 under TL Tara Rao and A2 under TL Tia Roy.

    T1 is Tara Rao's own login. A3 belongs to a different manager entirely.
    Staff time is 2h / 3h / 10h for A1 / A2 / A3.
    """
    session.add_all(
        [
            employee("M1", "Meera Shah"),
            employee("T1", "Tara Rao", manager="Meera Shah"),
            employee("A1", "Agent One", manager="Meera Shah", tl="Tara Rao"),
            employee("A2", "Agent Two", manager="Meera Shah", tl="Tia Roy"),
            employee("A3", "Agent Three", manager="Other Manager", tl="Other TL"),
            performance("A1", NOV_1, staff=2 * HOUR, talk=HOUR),
            performance("A2", NOV_1, staff=3 * HOUR, talk=2 * HOUR),
            performance("A3", NOV_1, staff=10 * HOUR, talk=5 * HOUR),
            adherence("A1", NOV_1, late=5),
            adherence("A3", NOV_1, late=5),
            shrinkage("A1", NOV_1, agents=1, present=1),
            shrinkage("A3", NOV_1, agents=1, present=1),
        ]
    )
    session.commit()


def viewer(role, emp_id):
    # Not saved: the scope only reads the role and the Employee ID.
    return User(
        full_name="Viewer",
        email="viewer@example.com",
        password_hash="unused",
        role=role,
        emp_id=emp_id,
    )


def test_admin_and_mis_are_not_limited(db):
    seed_team(db)

    assert get_dashboard_scope(db, viewer(UserRole.ADMIN, None)) is None
    assert get_dashboard_scope(db, viewer(UserRole.MIS, None)) is None
    assert get_dashboard_kpis(db).total_staff_time == Decimal("15.00")


def test_manager_sees_only_their_own_team(db):
    seed_team(db)
    scope = get_dashboard_scope(db, viewer(UserRole.MANAGER, "M1"))

    kpis = get_dashboard_kpis(db, scope=scope)
    agents = get_dashboard_agents(db, scope=scope)

    assert kpis.total_staff_time == Decimal("5.00")  # A1 + A2, not A3
    assert kpis.late_login_count == 1  # A1 only
    assert kpis.head_count == 1
    assert [row.emp_id for row in agents.items] == ["A1", "A2"]
    assert agents.total == 2


def test_tl_sees_only_the_agents_under_them(db):
    seed_team(db)
    scope = get_dashboard_scope(db, viewer(UserRole.TL, "T1"))

    kpis = get_dashboard_kpis(db, scope=scope)
    agents = get_dashboard_agents(db, scope=scope)

    assert kpis.total_staff_time == Decimal("2.00")
    assert [row.emp_id for row in agents.items] == ["A1"]


def test_scope_also_limits_trends_and_attendance(db):
    seed_team(db)
    scope = get_dashboard_scope(db, viewer(UserRole.MANAGER, "M1"))

    (point,) = get_dashboard_trends(db, scope=scope).points
    breakdown = get_dashboard_attendance(db, scope=scope)

    assert point.staff_time == 5.0
    assert point.talk_time == 3.0
    assert breakdown.total == 2


@pytest.mark.parametrize("emp_id", [None, "", "NOT-IN-MASTER"])
def test_manager_without_a_valid_employee_link_sees_nothing(db, emp_id):
    seed_team(db)
    scope = get_dashboard_scope(db, viewer(UserRole.MANAGER, emp_id))

    kpis = get_dashboard_kpis(db, scope=scope)

    assert kpis.total_staff_time == Decimal("0.00")
    assert kpis.missing_reports == ["APR", "SHIFT_ADHERENCE", "SHRINKAGE"]
    assert get_dashboard_agents(db, scope=scope).items == []
    assert get_dashboard_trends(db, scope=scope).points == []
    assert get_dashboard_attendance(db, scope=scope).total == 0


def _login_headers(client, make_user, *, role, email, emp_id=None):
    make_user(role=role, email=email, emp_id=emp_id)
    response = client.post(
        "/auth/login", json={"email": email, "password": "Password123"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_api_limits_a_manager_but_not_an_admin(client, engine, make_user):
    with Session(engine) as session:
        seed_team(session)
    manager = _login_headers(
        client, make_user, role=UserRole.MANAGER, email="meera@mismaster.com", emp_id="M1"
    )
    admin = _login_headers(
        client, make_user, role=UserRole.ADMIN, email="boss@mismaster.com"
    )

    mine = client.get("/dashboard/kpis", headers=manager)
    everyone = client.get("/dashboard/kpis", headers=admin)
    my_agents = client.get("/dashboard/agents", headers=manager)

    assert mine.status_code == 200
    assert Decimal(str(mine.json()["total_staff_time"])) == Decimal("5.00")
    assert Decimal(str(everyone.json()["total_staff_time"])) == Decimal("15.00")
    assert {row["emp_id"] for row in my_agents.json()["items"]} == {"A1", "A2"}


def test_api_gives_an_unlinked_tl_an_empty_dashboard(client, engine, make_user):
    with Session(engine) as session:
        seed_team(session)
    tl = _login_headers(
        client, make_user, role=UserRole.TL, email="unlinked.tl@mismaster.com"
    )

    kpis = client.get("/dashboard/kpis", headers=tl)
    agents = client.get("/dashboard/agents", headers=tl)

    assert kpis.status_code == 200
    assert Decimal(str(kpis.json()["total_staff_time"])) == Decimal("0")
    assert agents.json()["items"] == []


def test_api_dashboard_still_requires_login(client):
    assert client.get("/dashboard/kpis").status_code == 401


# --- Team filters (process / manager / TL / employee) ---------------------------


def test_tl_filter_narrows_an_unlimited_viewer(db):
    seed_team(db)
    scope = apply_dashboard_filters(None, tl="Tara Rao")

    kpis = get_dashboard_kpis(db, scope=scope)
    agents = get_dashboard_agents(db, scope=scope)

    assert kpis.total_staff_time == Decimal("2.00")
    assert [row.emp_id for row in agents.items] == ["A1"]


def test_filters_ignore_case_and_blank_values(db):
    seed_team(db)

    assert apply_dashboard_filters(None) is None
    assert apply_dashboard_filters(None, process="  ", tl="") is None
    scope = apply_dashboard_filters(None, process="sales", manager="MEERA SHAH")

    agents = get_dashboard_agents(db, scope=scope)

    assert {row.emp_id for row in agents.items} == {"A1", "A2"}


def test_employee_filter_shows_one_agent(db):
    seed_team(db)
    scope = apply_dashboard_filters(None, emp_id="a2")

    agents = get_dashboard_agents(db, scope=scope)

    assert [row.emp_id for row in agents.items] == ["A2"]
    assert get_dashboard_kpis(db, scope=scope).total_staff_time == Decimal("3.00")


def test_filters_can_never_widen_a_managers_scope(db):
    seed_team(db)
    manager_scope = get_dashboard_scope(db, viewer(UserRole.MANAGER, "M1"))
    # A3 belongs to another manager, so asking for them must show nothing.
    scope = apply_dashboard_filters(manager_scope, manager="Other Manager")

    assert get_dashboard_agents(db, scope=scope).items == []
    assert get_dashboard_kpis(db, scope=scope).total_staff_time == Decimal("0.00")
    narrowed = apply_dashboard_filters(manager_scope, tl="Tia Roy")
    assert [row.emp_id for row in get_dashboard_agents(db, scope=narrowed).items] == ["A2"]


def test_filter_options_are_limited_to_the_viewers_team(db):
    seed_team(db)
    manager_scope = get_dashboard_scope(db, viewer(UserRole.MANAGER, "M1"))

    mine = get_dashboard_filter_options(db, scope=manager_scope)
    everyone = get_dashboard_filter_options(db)

    assert mine.managers == ["Meera Shah"]
    assert mine.tls == ["Tara Rao", "Tia Roy"]
    assert "Other TL" in everyone.tls
    assert "Other Manager" in everyone.managers


def test_api_filters_apply_to_all_four_dashboard_routes(client, engine, make_user):
    with Session(engine) as session:
        seed_team(session)
    admin = _login_headers(
        client, make_user, role=UserRole.ADMIN, email="filters.admin@mismaster.com"
    )
    params = {"tl": "Tara Rao"}

    kpis = client.get("/dashboard/kpis", headers=admin, params=params)
    trends = client.get("/dashboard/trends", headers=admin, params=params)
    attendance = client.get("/dashboard/attendance", headers=admin, params=params)
    agents = client.get("/dashboard/agents", headers=admin, params=params)
    options = client.get("/dashboard/filters", headers=admin)

    assert Decimal(str(kpis.json()["total_staff_time"])) == Decimal("2.00")
    assert trends.json()["points"][0]["staff_time"] == 2.0
    assert attendance.json()["total"] == 1
    assert [row["emp_id"] for row in agents.json()["items"]] == ["A1"]
    assert "Tara Rao" in options.json()["tls"]
