import json
from datetime import date, datetime
from typing import NamedTuple

import httpx

from src.bot.constants import KYIV_TZ

DTEK_URL = "https://www.dtek-oem.com.ua/ua/shutdowns"
FACT_MARKER = "DisconSchedule.fact = "
# Hour keys are "1".."24" (1 = 00-01). Each value is yes | no | first | second (first/second = off for that half hour).
OFF_HALVES = {"yes": (False, False), "no": (True, True), "first": (True, False), "second": (False, True)}


class ParsedSchedule(NamedTuple):
    group_code: str
    day: date
    hours: dict[str, str]
    site_updated: str


async def fetch_schedules() -> list[ParsedSchedule]:
    """One request to DTEK; returns every group for every day the page publishes. Raises if the page is unusable."""
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = await client.get(DTEK_URL)
        resp.raise_for_status()

    html = resp.text
    marker_pos = html.find(FACT_MARKER)
    if marker_pos == -1:
        # Typically an Incapsula anti-bot challenge stub served with HTTP 200.
        raise RuntimeError(
            f"DTEK page has no schedule data (status={resp.status_code}, size={len(html)}): {html[:200]!r}"
        )
    fact, _ = json.JSONDecoder().raw_decode(html, marker_pos + len(FACT_MARKER))

    parsed = []
    for day_ts, groups in fact["data"].items():
        day = datetime.fromtimestamp(int(day_ts), KYIV_TZ).date()
        for key, hours in groups.items():
            if not key.startswith("GPV"):
                continue
            if set(hours) != {str(h) for h in range(1, 25)} or not set(hours.values()) <= OFF_HALVES.keys():
                raise ValueError(f"Unexpected DTEK hours format for {key} on {day}: {hours!r}")
            parsed.append(ParsedSchedule(key.removeprefix("GPV"), day, hours, fact["update"]))
    if not parsed:
        raise ValueError("DTEK page contained no group schedules")
    return parsed


def outage_intervals(hours: dict[str, str]) -> list[tuple[str, str]]:
    """Merge half-hour outage slots into ("HH:MM", "HH:MM") intervals."""
    slots = [off for h in range(1, 25) for off in OFF_HALVES[hours[str(h)]]]  # 48 half-hour slots

    intervals = []
    start = None
    for i, off in enumerate(slots + [False]):
        if off and start is None:
            start = i
        elif not off and start is not None:
            intervals.append((_fmt(start), _fmt(i)))
            start = None
    return intervals


def _fmt(slot: int) -> str:
    return f"{slot // 2:02d}:{slot % 2 * 30:02d}"
