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
deploy:
	git pull --ff-only
	docker compose build
	docker compose up -d postgres
	docker compose run --rm bot alembic upgrade head
	docker compose up -d

docker_migrate:
	docker compose run --rm bot alembic upgrade head

# First-time only: create tables and mark them as the current Alembic revision.
docker_init_db:
	docker compose up -d postgres
	docker compose run --rm bot python entrypoints/init_db.py
	docker compose run --rm bot alembic stamp head

ps:
	docker compose ps

logs_compact:
	docker compose logs -f bot scheduler pi_server

logs_all:
	docker compose logs -f

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
