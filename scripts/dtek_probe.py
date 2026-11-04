"""Standalone probe: can a headless browser get DTEK's schedule from this machine when plain HTTP cannot?

Not part of the bot. Run it on the droplet (see "How to run" below) and read the verdict at the end.

It makes two requests to the DTEK page:
  1. plain HTTP (what src/dtek.py does today)  -> expected to be the Incapsula challenge stub
  2. headless Chromium via Playwright           -> if this finds `DisconSchedule.fact`, the browser approach works

See scripts/README.md for how to run it. Exit code: 0 = browser got the data, 1 = it did not.
"""

import argparse
import json
import sys
import time
import urllib.request

DEFAULT_URL = "https://www.dtek-oem.com.ua/ua/shutdowns"
FACT_MARKER = "DisconSchedule.fact = "
USER_AGENT = "Mozilla/5.0"


def extract_fact(html: str):
    pos = html.find(FACT_MARKER)
    if pos == -1:
        return None
    fact, _ = json.JSONDecoder().raw_decode(html, pos + len(FACT_MARKER))
    return fact


def probe_plain(url: str):
    print("== 1. plain HTTP ==")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            print(f"status={resp.status} size={len(html)}")
    except Exception as e:
        print(f"request failed: {e!r}")
        return None
    fact = extract_fact(html)
    print("marker found" if fact else f"marker NOT found, body starts: {html[:150]!r}")
    return fact


def probe_browser(url: str, attempts: int = 3, settle_seconds: int = 5):
    from playwright.sync_api import sync_playwright

    print("\n== 2. headless Chromium ==")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            for attempt in range(1, attempts + 1):
                started = time.monotonic()
                try:
                    resp = page.goto(url, wait_until="load", timeout=60_000)
                    # The challenge script may reload the page once it has set its cookie.
                    page.wait_for_timeout(settle_seconds * 1000)
                    html = page.content()
                    status = resp.status if resp else None
                except Exception as e:
                    print(f"attempt {attempt}: navigation failed: {e!r}")
                    continue
                fact = extract_fact(html)
                print(
                    f"attempt {attempt}: status={status} size={len(html)} "
                    f"took={time.monotonic() - started:.1f}s marker={'found' if fact else 'NOT found'}"
                )
                if fact:
                    return fact
                print(f"  body starts: {html[:150]!r}")
        finally:
            browser.close()
    return None


def describe(fact: dict, group: str | None):
    print("\n== schedule data ==")
    print(f"update={fact.get('update')!r} today={fact.get('today')}")
    days = fact.get("data", {})
    print(f"days={list(days)}")
    today_groups = days.get(str(fact.get("today")), {})
    print(f"groups today: {sorted(today_groups)}")
    if group:
        hours = today_groups.get(f"GPV{group}")
        print(f"GPV{group}: {json.dumps(hours, ensure_ascii=False) if hours else 'NOT FOUND'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--group", help='group without the GPV prefix, e.g. "3.1"')
    args = parser.parse_args()

    plain = probe_plain(args.url)
    browser = probe_browser(args.url)

    print("\n== verdict ==")
    print(f"plain HTTP: {'OK' if plain else 'blocked'}")
    print(f"browser:    {'OK' if browser else 'blocked'}")
    if browser:
        describe(browser, args.group)
        return 0
    print("Browser did not get the data: the block is likely IP-based. Try another egress IP (e.g. the Pi).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
