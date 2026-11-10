MSG ?= auto
PI_COMPOSE = docker compose -f docker-compose.pi.yml

# --- Local development (uv) ---

install:
	uv sync

format:
	uv run ruff format .

fix:
	uv run ruff check --fix .

run_scheduler:
	uv run python entrypoints/scheduler.py

run_bot:
	uv run python entrypoints/bot.py

run_maintenance:
	uv run python entrypoints/maintenance.py

run_pi_client:
	uv run python entrypoints/start_pi_client.py

run_pi_server:
	uv run python entrypoints/start_pi_server.py

init_db:
	uv run python entrypoints/init_db.py

refresh_db:
	uv run python entrypoints/refresh_db.py

migrations:
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate:
	uv run alembic upgrade head

downgrade:
	uv run alembic downgrade -1

# --- Droplet (docker-compose.yml) ---

docker_build:
	docker compose up -d --build

docker_stop:
	docker compose stop

# Pull latest code, apply migrations, rebuild and restart changed services.
# pi_server goes first and we wait one Pi heartbeat interval (10s by default) before restarting the scheduler,
# so it never reads a stale heartbeat left over from the restart and reports a false status change.
HEARTBEAT_SETTLE_SECONDS ?= 15

deploy:
	git pull --ff-only
	docker compose build
	docker compose up -d postgres
	docker compose run --rm bot alembic upgrade head
	docker compose up -d --wait pi_server
	sleep $(HEARTBEAT_SETTLE_SECONDS)
	docker compose up -d

# Bot-only deploy: pull, rebuild the image and force-recreate just the bot container.
# Skips migrations; scheduler and pi_server keep running on their current containers.
deploy_bot:
	git pull --ff-only
	docker compose build bot
	docker compose up -d --no-deps --force-recreate bot

# Also the first-time setup: migrations build the schema from an empty database.
docker_migrate:
	docker compose run --rm bot alembic upgrade head

ps:
	docker compose ps

logs_compact:
	docker compose logs -f bot scheduler pi_server

logs_all:
	docker compose logs -f

logs_bot:
	docker compose logs -f bot

logs-last-100:
	docker compose logs --tail=100

# --- Raspberry Pi (docker-compose.pi.yml) ---

pi_up:
	$(PI_COMPOSE) up -d --build

pi_down:
	$(PI_COMPOSE) down

pi_restart:
	$(PI_COMPOSE) restart

# Pull latest code and rebuild/restart the client.
pi_deploy:
	git pull --ff-only
	$(PI_COMPOSE) up -d --build

pi_logs:
	$(PI_COMPOSE) logs -f --tail=100

pi_ps:
	$(PI_COMPOSE) ps

pi_temp:
	vcgencmd measure_temp
