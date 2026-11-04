import json
from datetime import datetime

import httpx

from src.bot.constants import KYIV_TZ

DTEK_URL = "https://www.dtek-oem.com.ua/ua/shutdowns"
FACT_MARKER = "DisconSchedule.fact = "
# Hour keys are "1".."24" (1 = 00-01). Each value is yes | no | first | second (first/second = off for that half hour).
OFF_HALVES = {"yes": (False, False), "no": (True, True), "first": (True, False), "second": (False, True)}


async def fetch_today_schedule(group: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (update timestamp, merged outage intervals as ("HH:MM", "HH:MM")) for today's DTEK group, e.g. "2.2"."""
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
    return fact["update"], intervals


def _fmt(slot: int) -> str:
    return f"{slot // 2:02d}:{slot % 2 * 30:02d}"


def today_label() -> str:
    return datetime.now(KYIV_TZ).strftime("%d.%m.%Y")
