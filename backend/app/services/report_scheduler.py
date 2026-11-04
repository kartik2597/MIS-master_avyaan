"""Build the scheduled daily, weekly and monthly MIS reports in the background.

A small loop runs inside the API process. Every few minutes it checks whether a
report is due and not yet built, and builds it with generate_scheduled_report
(which saves the Excel and PDF files and emails them when SMTP is configured).

  daily    every day
  weekly   on Mondays
  monthly  on the 1st of the month

Nothing is built before APP_AUTO_REPORTS_HOUR. A report is skipped when its files
already exist in storage/reports, so restarting the server never builds it twice.
If the server was down for the whole day a report was due, that report is not
built later; it can still be downloaded from the Reports endpoint.

With several backend workers each one runs this loop. The "files already exist"
check makes duplicates unlikely but does not prevent a race; run one scheduler
(for example a single worker, or a separate job) in production.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import SessionLocal
from app.services.report_export import generate_scheduled_report, period_for


logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 600
# Give up on one report for the day after this many failed tries, so a permanent
# problem (a broken PDF library, say) does not retry and log every ten minutes.
MAX_ATTEMPTS_PER_REPORT = 3

_attempts: dict[str, int] = {}


def due_report_kinds(today: date) -> list[str]:
    """The report kinds that should exist by the end of this day."""
    kinds = ["daily"]
    if today.weekday() == 0:
        kinds.append("weekly")
    if today.day == 1:
        kinds.append("monthly")
    return kinds


def report_files_exist(kind: str, today: date) -> bool:
    """Whether both files of this report are already in storage/reports."""
    date_from, date_to = period_for(kind, today)
    stem = f"{kind}_{date_from.isoformat()}_{date_to.isoformat()}"
    return all(
        (settings.REPORTS_PATH / f"{stem}.{extension}").exists()
        for extension in ("xlsx", "pdf")
    )


def run_due_reports(
    now: datetime,
    session_factory: Callable[[], Session] = SessionLocal,
) -> list[str]:
    """Build every report that is due and missing. Returns the kinds it built.

    One failing report never stops the others and never raises.
    """
    if now.hour < settings.AUTO_REPORTS_HOUR:
        return []

    today = now.date()
    built: list[str] = []
    for kind in due_report_kinds(today):
        if report_files_exist(kind, today):
            continue
        key = f"{kind}:{today.isoformat()}"
        if _attempts.get(key, 0) >= MAX_ATTEMPTS_PER_REPORT:
            continue
        _attempts[key] = _attempts.get(key, 0) + 1

        db = session_factory()
        try:
            generate_scheduled_report(db, kind, today)
            built.append(kind)
        except Exception:
            logger.exception("Scheduled %s report failed (attempt %s)", kind, _attempts[key])
            db.rollback()
        finally:
            db.close()
    return built


async def _scheduler_loop() -> None:
    logger.info(
        "Report scheduler started: builds reports after %02d:00, checks every %s seconds",
        settings.AUTO_REPORTS_HOUR,
        CHECK_INTERVAL_SECONDS,
    )
    while True:
        try:
            # Report building is blocking work, so keep it off the event loop.
            await asyncio.to_thread(run_due_reports, datetime.now())
        except Exception:
            logger.exception("Scheduled report check failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_report_scheduler() -> asyncio.Task | None:
    """Start the background loop, or return None when APP_AUTO_REPORTS_ENABLED is off."""
    if not settings.AUTO_REPORTS_ENABLED:
        logger.info("Report scheduler is disabled (APP_AUTO_REPORTS_ENABLED=false)")
        return None
    return asyncio.create_task(_scheduler_loop())
