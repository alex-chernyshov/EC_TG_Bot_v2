from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.models import DtekSchedule
from src.dtek import fetch_schedules
from src.logger.main import logger

REFRESH_INTERVAL_SECONDS = 3600
JITTER = 0.1
FAILURE_BACKOFF_START_SECONDS = 900
FAILURE_BACKOFF_MAX_SECONDS = 6 * 3600
JOB_ID = "dtek_refresh"

_backoff = FAILURE_BACKOFF_START_SECONDS


async def seconds_until_next_fetch(session: AsyncSession) -> float:
    """Based on the DB, so restarts/deploys don't trigger an extra request to DTEK."""
    last_fetched = (await session.execute(select(func.max(DtekSchedule.date_fetched)))).scalar_one()
    if last_fetched is None:
        return 0
    elapsed = (datetime.now(UTC) - last_fetched).total_seconds()
    return max(0, REFRESH_INTERVAL_SECONDS - elapsed)


async def refresh_once(session: AsyncSession) -> None:
    schedules = await fetch_schedules()
    stmt = insert(DtekSchedule).values(
        [
            {"group_code": s.group_code, "day": s.day, "hours": s.hours, "site_updated": s.site_updated}
            for s in schedules
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["group_code", "day"],
        set_={"hours": stmt.excluded.hours, "site_updated": stmt.excluded.site_updated, "date_fetched": func.now()},
    )
    await session.execute(stmt)
    await session.commit()
    logger.info(f"DTEK schedules refreshed: {len(schedules)} group/day rows")


async def dtek_job(scheduler: AsyncIOScheduler, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Regular runs follow the hourly trigger; "still fresh" and failures move the next run explicitly."""
    global _backoff
    try:
        async with session_factory() as session:
            delay = await seconds_until_next_fetch(session)
            if delay > 0:
                logger.info(f"DTEK schedules are fresh, next fetch in {delay:.0f}s")
            else:
                await refresh_once(session)
                _backoff = FAILURE_BACKOFF_START_SECONDS
                return
    except Exception as exc:
        logger.error(f"DTEK refresh failed, retrying in {_backoff}s: {exc!r}")
        delay = _backoff
        _backoff = min(_backoff * 2, FAILURE_BACKOFF_MAX_SECONDS)
    scheduler.modify_job(JOB_ID, next_run_time=datetime.now(UTC) + timedelta(seconds=delay))


def add_dtek_job(scheduler: AsyncIOScheduler, session_factory: async_sessionmaker[AsyncSession]) -> None:
    scheduler.add_job(
        dtek_job,
        IntervalTrigger(seconds=REFRESH_INTERVAL_SECONDS, jitter=REFRESH_INTERVAL_SECONDS * JITTER),
        args=[scheduler, session_factory],
        id=JOB_ID,
        next_run_time=datetime.now(UTC),
    )
