import asyncio
import json
import time
from datetime import date, datetime
from typing import NamedTuple

import httpx

from src.bot.constants import KYIV_TZ
from src.logger.main import logger

DTEK_URL = "https://www.dtek-oem.com.ua/ua/shutdowns"
FACT_MARKER = "DisconSchedule.fact = "
# Hour keys are "1".."24" (1 = 00-01). Each value is yes | no | first | second (first/second = off for that half hour).
CACHE_TTL_SECONDS = 3600
RETRY_BACKOFF_SECONDS = 60
OFF_HALVES = {"yes": (False, False), "no": (True, True), "first": (True, False), "second": (False, True)}


class Schedule(NamedTuple):
    day: date
    updated: str
    intervals: list[tuple[str, str]]  # merged outages as ("HH:MM", "HH:MM")


# group -> (monotonic fetch time, schedule)
_cache: dict[str, tuple[float, Schedule]] = {}
_last_failure = 0.0
_lock = asyncio.Lock()


async def get_schedule(group: str) -> Schedule:
    """Cached for CACHE_TTL_SECONDS and invalidated at Kyiv midnight. The entry is keyed by the day DTEK reports,
    so stale data served just after midnight is never treated as fresh.

    If DTEK is unreachable, the last known schedule is returned (check `.day`); raises only when there is none."""
    global _last_failure
    async with _lock:  # one upstream request on expiry, not one per concurrent user
        cached = _cache.get(group)
        if cached:
            fetched_at, schedule = cached
            is_fresh = (
                schedule.day == datetime.now(KYIV_TZ).date() and time.monotonic() - fetched_at < CACHE_TTL_SECONDS
            )
            # After a failure keep serving stale data instead of making every click wait on a dead upstream.
            in_backoff = time.monotonic() - _last_failure < RETRY_BACKOFF_SECONDS
            if is_fresh or in_backoff:
                logger.info(f"DTEK schedule from cache (group={group}, stale={not is_fresh})")
                return schedule
        try:
            schedule = await _fetch_schedule(group)
        except Exception:
            if not cached:
                raise
            _last_failure = time.monotonic()
            logger.exception("DTEK fetch failed, serving stale schedule")
            return cached[1]
        logger.info(f"DTEK schedule from HTTP response (group={group})")
        _cache[group] = (time.monotonic(), schedule)
        return schedule


async def _fetch_schedule(group: str) -> Schedule:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = await client.get(DTEK_URL)
        resp.raise_for_status()

    html = resp.text
    fact, _ = json.JSONDecoder().raw_decode(html, html.index(FACT_MARKER) + len(FACT_MARKER))
    hours = fact["data"][str(fact["today"])][f"GPV{group}"]

    slots = [off for h in range(1, 25) for off in OFF_HALVES[hours[str(h)]]]  # 48 half-hour slots

    intervals = []
    start = None
    for i, off in enumerate(slots + [False]):
        if off and start is None:
            start = i
        elif not off and start is not None:
            intervals.append((_fmt(start), _fmt(i)))
            start = None
    return Schedule(datetime.fromtimestamp(fact["today"], KYIV_TZ).date(), fact["update"], intervals)


def _fmt(slot: int) -> str:
    return f"{slot // 2:02d}:{slot % 2 * 30:02d}"
