# Power Status App

![System design](docs/system_design.png)

Telegram bot and heartbeat pipeline that tells users when the power (and the building generator) goes on or off.

A Raspberry Pi plugged into the mains sends a heartbeat every few seconds. When the power goes out, the Pi goes dark, the
heartbeats stop, and the bot notifies subscribers. A second Pi on the generator line works the same way.

## How it works

Four processes share one Postgres database. They never talk to each other directly, only through the DB.

| Process     | Runs on       | What it does                                                                        |
|-------------|---------------|-------------------------------------------------------------------------------------|
| `pi_client` | each Pi       | `GET http://DROPLET_IP:DROPLET_PORT/heartbeat?timestamp=&label=` with a Bearer token |
| `pi_server` | droplet       | FastAPI app that upserts one `heartbeat` row per `label`                            |
| `scheduler` | droplet       | Every N s marks each label on/off by heartbeat age and writes `statuses` on change  |
| `bot`       | droplet       | Telegram UI, and broadcasts `POWER` status changes to subscribed users             |

`HEARTBEAT_LABEL` on each Pi must be exactly one of `POWER` or `GENERATOR` (`src/enums.py`). Generator status is not
pushed; users check it on demand.

```
 Pi (POWER) ─┐
             ├─ HTTP :5566 ─► pi_server ─► Postgres ◄─ scheduler
 Pi (GEN) ───┘                               ▲
                                             └──── bot ◄─► Telegram
```

## Tech stack

Python 3.14, uv, FastAPI + Uvicorn, python-telegram-bot, SQLAlchemy (async) + asyncpg, Alembic, Loguru, Docker Compose,
Ruff.

## Repository layout

```
docker/Dockerfile        # single image for every process (DEPS_GROUP build arg picks deps)
docker-compose.yml       # droplet stack: postgres, bot, scheduler, pi_server
docker-compose.pi.yml    # Raspberry Pi stack: pi_client only
pyproject.toml, uv.lock  # dependencies; groups: server, pi, dev
entrypoints/             # runnable scripts (always start processes from here)
src/bot/                 # Telegram handlers, jobs, keyboards, lang packs
src/pi_server/           # heartbeat API
src/pi_client/           # heartbeat sender
src/scheduler/           # power status detector
src/db/                  # models, init/refresh helpers
alembic/                 # migrations
```

## Configuration

All config lives in a `.env` file in the repo root (gitignored). Start from the template:

```bash
cp .env_example .env
```

The template is split into droplet, shared, and Pi sections. Each machine only needs its own section, but an extra
variable does no harm.

| Variable                                  | Where   | Notes                                                       |
|-------------------------------------------|---------|-------------------------------------------------------------|
| `POSTGRES_PASSWORD`                       | droplet | required                                                    |
| `POSTGRES_IMAGE_TAG`                      | droplet | **pin the major version** (e.g. `18`), see below            |
| `TELEGRAM_TOKEN`                          | droplet | required, from BotFather                                    |
| `PI_SERVER_PORT`                          | droplet | public heartbeat port, default `5566`                       |
| `LISTEN_HEARTBEAT_INTERVAL_SECONDS`       | droplet | scheduler tick, default `10`                                |
| `BOT_NOTIFICATION_POLL_INTERVAL_SECONDS`  | droplet | default `60`                                                |
| `HEARTBEAT_TOKEN`                         | both    | must be identical everywhere; auth is off if empty          |
| `DROPLET_IP`, `DROPLET_PORT`              | Pi      | where `pi_server` is reachable                              |
| `HEARTBEAT_LABEL`                         | Pi      | `POWER` or `GENERATOR`                                      |
| `SEND_HEARTBEAT_INTERVAL_SECONDS`         | Pi      | default `10`; keep it ≤ the scheduler interval              |

Optional tuning (not in the template): `LOG_LEVEL`, `LOGURU_COLORIZE`, `HEARTBEAT_PATH`, `HEARTBEAT_TIMEOUT`,
`BOT_NOTIF_RATE_LIMIT_PER_SEC`, `BOT_NOTIF_MAX_CONCURRENCY`, `BOT_BUTTON_RATE_LIMIT_PER_SEC`.

Containers get `.env` through `env_file` at runtime. It is never copied into an image (`.dockerignore`).

## Droplet deployment

Prerequisites: Docker Engine with the Compose plugin, `make`, `git`. The pi_server port (`5566`) must be open in the
firewall. Postgres stays bound to `127.0.0.1`.

### First time

```bash
git clone <repo-url> EC_TG_Bot_v2 && cd EC_TG_Bot_v2
cp .env_example .env && nano .env   # fill droplet + shared sections
make docker_init_db                 # start postgres, create tables, stamp Alembic head
make docker_build                   # build and start everything
make logs_compact
```

> **Already ran `init_db.py` by hand?** `create_all` doesn't record an Alembic revision, so the first
> `alembic upgrade head` would try to recreate existing tables. Run this once:
> `docker compose run --rm bot alembic stamp head`

### Updating

```bash
make deploy    # git pull, build, alembic upgrade head, restart changed containers
```

### Day-to-day

```bash
make ps                # container status
make logs_compact      # follow bot/scheduler/pi_server
make logs-last-100
make docker_stop
make docker_migrate    # apply migrations only
```

Every service has `restart: unless-stopped`, so the stack comes back after crashes and droplet reboots.

### Maintenance mode

Run the stub bot that tells users "maintenance in progress", for example during a long migration:

```bash
docker compose stop bot
docker compose run -d --rm --name maintenance bot python entrypoints/maintenance.py
# ...do the work...
docker stop maintenance && docker compose up -d bot
```

### Postgres version

`POSTGRES_IMAGE_TAG=latest` will eventually pull a new major version, and that version can't open the old data
directory. Check what you're running and pin it in `.env`:

```bash
docker compose exec postgres postgres --version   # e.g. "postgres (PostgreSQL) 18.1" -> POSTGRES_IMAGE_TAG=18
```

## Raspberry Pi deployment

Each Pi runs one container, `pi_client`, from `docker-compose.pi.yml`. It works on 64-bit and 32-bit Raspberry Pi OS.

### First time

```bash
# 1. Install Docker (includes the Compose plugin) and allow your user to run it
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
sudo systemctl enable docker      # start the Docker daemon on boot (usually already enabled)
# log out and back in so the group change applies

# 2. Get the code and configure
sudo apt install -y git make
git clone <repo-url> EC_TG_Bot_v2 && cd EC_TG_Bot_v2
cp .env_example .env && nano .env  # fill the Pi + shared sections; HEARTBEAT_LABEL=POWER or GENERATOR

# 3. Start
make pi_up
make pi_logs    # expect "Heartbeat sent. Status code: 200"
```

`restart: unless-stopped` plus the Docker daemon starting on boot means the client comes back on its own after a crash,
a power cut, or a reboot. That last case is the one that matters here. It stays down only after `make pi_down`.

### Migrating from the old systemd unit

If a Pi still has the old `pi-client` systemd service, remove it first so two clients don't run at once:

```bash
sudo systemctl disable --now pi-client
sudo rm /etc/systemd/system/pi-client.service && sudo systemctl daemon-reload
```

### Day-to-day

```bash
make pi_deploy   # git pull + rebuild + restart
make pi_logs
make pi_ps
make pi_restart
make pi_down
make pi_temp     # CPU temperature
```

## Local development

Requires [uv](https://docs.astral.sh/uv/). It installs the right Python (from `.python-version`) on its own.

```bash
uv sync              # creates .venv with all dependency groups
cp .env_example .env
docker compose up -d postgres
make init_db         # or: make migrate
make run_pi_server   # / run_scheduler / run_bot / run_pi_client
```

Dependencies:

```bash
uv add --group server <pkg>   # droplet-side dependency
uv add --group pi <pkg>       # pi_client dependency
uv add <pkg>                  # needed by both
uv lock --upgrade             # bump everything within constraints
```

Commit `uv.lock`. Docker builds use `uv sync --locked` and fail if the lockfile is stale.

Lint/format: `make fix`, `make format`. Migrations: `make migrations MSG="describe change"`, `make migrate`,
`make downgrade`.
