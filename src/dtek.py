import base64
import re
import secrets
from datetime import date, datetime
from typing import NamedTuple
from urllib.parse import unquote

import httpx

from src.bot.constants import KYIV_TZ

# The HTML page (/ua/shutdowns) sits behind an Incapsula JS challenge; the site's own AJAX endpoint does not.
DTEK_BASE_URL = "https://www.dtek-oem.com.ua"
DTEK_AJAX_URL = f"{DTEK_BASE_URL}/ua/ajax"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# Any "update" older than the site's current one makes checkDisconUpdate return the full fact schedule.
FORCE_UPDATE = "01.01.2000 00:00"
# Yii2 stores the raw CSRF token PHP-serialized inside the _csrf-dtek-oem cookie.
CSRF_TOKEN_RE = re.compile(r'i:1;s:\d+:"([^"]+)"')
# Hour keys are "1".."24" (1 = 00-01). Each value is yes | no | first | second (first/second = off for that half hour).
OFF_HALVES = {"yes": (False, False), "no": (True, True), "first": (True, False), "second": (False, True)}


class ParsedSchedule(NamedTuple):
    group_code: str
    day: date
    hours: dict[str, str]
    site_updated: str


async def fetch_schedules() -> list[ParsedSchedule]:
    """Returns every group for every day DTEK publishes. Raises if the response is unusable."""
    fact = await _fetch_fact()

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


async def _fetch_fact() -> dict:
    """Two POSTs: the first (no token) is rejected with 400 but sets the CSRF cookie, the second fetches the data."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": DTEK_BASE_URL,
        "Referer": f"{DTEK_BASE_URL}/ua/shutdowns",
    }
    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        await client.post(DTEK_AJAX_URL, data={"method": "getHomeNum"})
        cookie = next((v for k, v in client.cookies.items() if k.startswith("_csrf")), "")
        token = CSRF_TOKEN_RE.search(unquote(cookie))
        if token is None:
            raise RuntimeError(f"DTEK did not issue a CSRF cookie (cookies={list(client.cookies.keys())})")

        resp = await client.post(
            DTEK_AJAX_URL,
            data={"method": "checkDisconUpdate", "update": FORCE_UPDATE},
            headers={"X-CSRF-Token": _mask_csrf_token(token.group(1))},
        )
        resp.raise_for_status()

    try:
        return resp.json()["fact"]
    except (ValueError, KeyError):
        # Typically an Incapsula anti-bot challenge stub served with HTTP 200.
        raise RuntimeError(
            f"DTEK response has no schedule data (status={resp.status_code}, size={len(resp.text)}): {resp.text[:200]!r}"
        ) from None


def _mask_csrf_token(token: str) -> str:
    """Yii2 Security::maskToken: base64url(mask + (mask XOR token))."""
    raw = token.encode()
    mask = secrets.token_bytes(len(raw))
    return base64.urlsafe_b64encode(mask + bytes(a ^ b for a, b in zip(mask, raw))).decode()


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
