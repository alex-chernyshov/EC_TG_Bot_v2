import asyncio
import random
from datetime import UTC, datetime

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


async def run_dtek_loop(session_factory: async_sessionmaker[AsyncSession]) -> None:
    backoff = FAILURE_BACKOFF_START_SECONDS
    while True:
        try:
            async with session_factory() as session:
                delay = await seconds_until_next_fetch(session)
                if delay > 0:
                    logger.info(f"DTEK schedules are fresh, next fetch in {delay:.0f}s")
                else:
                    await refresh_once(session)
                    backoff = FAILURE_BACKOFF_START_SECONDS
                    delay = REFRESH_INTERVAL_SECONDS
            delay *= 1 + random.uniform(0, JITTER)
        except Exception as exc:
            logger.error(f"DTEK refresh failed, retrying in {backoff}s: {exc!r}")
            delay = backoff
            backoff = min(backoff * 2, FAILURE_BACKOFF_MAX_SECONDS)
        await asyncio.sleep(delay)
