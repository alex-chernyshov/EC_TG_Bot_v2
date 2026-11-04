# scripts

Standalone helpers that are not part of the bot. They import nothing from `src/`.

## dtek_probe.py

Checks whether a headless browser can fetch DTEK's schedule from the current machine when plain HTTP cannot
(the site is behind Incapsula bot protection, which serves a JS challenge stub instead of the page).

It makes two requests to the DTEK page:

1. Plain HTTP, which is what `src/dtek.py` does today. Expected to return the challenge stub.
2. Headless Chromium via Playwright (up to 3 attempts, 5 s settle time each). Succeeds if the rendered page contains
   `DisconSchedule.fact`.

### Run on the droplet

From the repo root, with Docker installed. Nothing is installed on the host and the container is removed afterwards.

```bash
git pull   # or scp scripts/dtek_probe.py to the droplet

docker run --rm -v "$PWD/scripts/dtek_probe.py:/probe.py:ro" python:3.12-slim bash -c \
  "pip install -q playwright && playwright install --with-deps chromium >/dev/null && python /probe.py --group 3.1"
```

Options:

- `--group 3.1`: group without the `GPV` prefix; prints that group's hours for today. Omit to skip.
- `--url <page>`: another DTEK region page. Default is `https://www.dtek-oem.com.ua/ua/shutdowns`.

The first run downloads about 400 MB (Chromium and system libraries) and takes a few minutes. On a small droplet watch
the RAM: a `Killed` message means the container was OOM-killed, which also tells you Chromium is too heavy for that box.

Exit code: `0` if the browser got the data, `1` if not.

### Reading the result

| plain HTTP | browser | Meaning |
| ---------- | ------- | ------- |
| blocked | OK | The browser approach works from this IP. Choose between a Playwright sidecar and a GitHub Actions fetcher. |
| blocked | blocked | The block is likely IP-based. Try another egress IP (for example the Pi) or fetch from GitHub Actions. |
| OK | OK | Not blocked right now. It may be intermittent, so rerun at different hours. |
