# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All common tasks are in the `Makefile`:

```bash
make install         # uv sync (all dependency groups)
make format          # uv run ruff format .
make fix             # uv run ruff check --fix .

make run_bot | run_scheduler | run_pi_server | run_pi_client | run_maintenance

make init_db         # Base.metadata.create_all (first-time setup)
make refresh_db      # DROPS all tables and recreates them
make migrations MSG="describe change"   # alembic revision --autogenerate
make migrate         # alembic upgrade head
make downgrade       # alembic downgrade -1

# Droplet (docker-compose.yml)
make docker_init_db  # first time: postgres up, init_db.py, alembic stamp head
make docker_build    # docker compose up -d --build (postgres, bot, scheduler, pi_server)
make deploy          # git pull, build, alembic upgrade head, up -d
make logs_compact    # follow bot/scheduler/pi_server logs

# Raspberry Pi (docker-compose.pi.yml)
make pi_up | pi_deploy | pi_logs | pi_restart | pi_down
```

Dependencies are managed with uv (`pyproject.toml` + `uv.lock`, `package = false`). Groups: `server` (droplet processes), `pi` (pi_client only, kept minimal so the Pi never builds asyncpg etc.), `dev` (ruff). Base `dependencies` are shared by both. Local `uv sync` installs all groups.

The project has no test suite. Lint uses Ruff (`ruff.toml`: line length 120, rules `E4,E7,E9,F`; `__init__.py` files are excluded).

## Configuration

- Env template is `.env_example` (the README still says `.env.example`, which is out of date). Copy it to `.env`; `.env` and `.env.*` (for example `.env.prod`) are gitignored.
- Every entrypoint in `entrypoints/` adds the repo root to `sys.path` and calls `load_dotenv()` before importing `src.*`, so run scripts from those entrypoints rather than `python -m`.
- `src/utils.py:get_database_url()` builds the `postgresql+asyncpg://` URL from `POSTGRES_*` vars. `POSTGRES_HOST` defaults to `127.0.0.1` locally; Compose sets it to `postgres`.
- Extra bot tuning env vars that are not in `.env_example`: `BOT_NOTIF_RATE_LIMIT_PER_SEC`, `BOT_NOTIF_MAX_CONCURRENCY`, `BOT_BUTTON_RATE_LIMIT_PER_SEC`.
- The code needs Python 3.11+ (`enum.StrEnum`, `datetime.UTC`), and the Docker images use 3.14. Ruff's `target-version = "py39"` is misleading.
- Containers receive `.env` via compose `env_file` at runtime; `.dockerignore` keeps it out of images. The app services override `POSTGRES_HOST=postgres`/`POSTGRES_PORT=5432`.
- `docker/Dockerfile` is the single image for all processes; the `DEPS_GROUP` build arg (`server` | `pi`) selects the uv group and each compose service sets its own `command`. uv is installed via pip because the `ghcr.io/astral-sh/uv` image has no `linux/arm/v7` build.

## Architecture

Four independent processes share one Postgres database. They communicate only through the DB, never with each other directly:

1. **pi_client** (`src/pi_client/main.py`) runs on a Raspberry Pi as a Docker container from `docker-compose.pi.yml` (`restart: unless-stopped`). Every `SEND_HEARTBEAT_INTERVAL_SECONDS` it sends `GET {DROPLET_IP}:{DROPLET_PORT}{HEARTBEAT_PATH}?timestamp=&label=` with a Bearer `HEARTBEAT_TOKEN`.
2. **pi_server** (`src/pi_server/main.py`, FastAPI) upserts a single `heartbeat` row per `label` with the latest timestamp. Token checking only happens when `HEARTBEAT_TOKEN` is set.
3. **scheduler** (`src/scheduler/main.py`) polls every `LISTEN_HEARTBEAT_INTERVAL_SECONDS`. For each `Label` in `src/enums.py` (`POWER`, `GENERATOR`), the device counts as "on" if its last heartbeat is newer than `interval * WAIT_TILL_MAKE_DECISION` seconds. It inserts a `statuses` row only when the value changes. `HEARTBEAT_LABEL` on each Pi must exactly match one of these enum values. If a label has no heartbeat row, the scheduler `return`s and skips the remaining labels for that tick.
4. **bot** (`src/bot/main.py`, python-telegram-bot with job-queue) handles user interaction and runs a repeating job (`src/bot/jobs/power_notifications.py`). The job compares the two latest `POWER` statuses and broadcasts changes to users with `notifs_enabled`. `last_notified_status_id` is kept only in memory (`bot_data`), so after a restart the current latest status counts as already notified. Generator status is never pushed; it is read on demand by `handlers/message/gen_status.py` and compared with the hardcoded schedules in `src/bot/constants.py` (Kyiv time).

`entrypoints/maintenance.py` runs a separate stub bot that answers every message with a "maintenance" notice. Run it in place of the real bot during updates.

### Bot internals

- Shared state lives in `app.bot_data`, set up in `start_bot()`: `session_factory`, `rate_limiter` (aiolimiter), `semaphore`, `languages`, and the per-user button rate-limit buckets. Handlers read their dependencies from there.
- **Routing by button text:** reply-keyboard buttons are matched with a regex built from that button's text in every language pack (`build_button_pattern`). Renaming a `BTN_*` string in a lang pack automatically changes routing.
- Message handlers for keyboard buttons are wrapped in `@button_rate_limited` (`src/bot/utils.py`).
- Registration and settings use inline callbacks (`notif_yes|no`, then `night_sound_yes|no`) plus `context.user_data["registering_user_id"]` / `["is_reconfiguration"]`. `/settings` reuses the registration flow.
- Outgoing broadcasts go through `send_message_with_retry` (tenacity retries, semaphore, rate limiter). It defaults to **MarkdownV2**, so literal `.`, `!`, `-` and similar characters in notification/lang strings must be escaped (`\\.`).
- `/msgAll <text>` is an admin-only broadcast, gated by `users.is_admin`, and is sent as plain text.
- At night (22:00–08:00 Kyiv), notifications are sent silently for users with `night_notif_sound_enabled = False`.

### Localization

`src/bot/lang_pack/`: `BaseLangPack` defines every string key as a `{{KEY}}` placeholder. `uk`, `ru`, `en`, `cs` subclass it, and `LangContainer` maps Telegram `language_code` to a pack. **The default/fallback is `ru`.** When you add a user-facing string, add it to `BaseLangPack` and to all four packs.

### Database

Models are in `src/db/models/` and re-exported via `src/db/models/__init__.py`, which Alembic's `env.py` imports for autogenerate. Schema changes go through Alembic migrations in `alembic/versions/`. `init_db` and `refresh_db` use `create_all`/`drop_all` directly and bypass Alembic.

### Logging

Use `from src.logger.main import logger`. The log format includes `{extra[username]}`, so add per-user context with `logger.bind(username=get_user_identity_from_update(update))`. The default value is `"system"`.
