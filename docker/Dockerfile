# One image for every process. DEPS_GROUP picks the dependency group from pyproject.toml:
#   server -> bot, scheduler, pi_server (droplet)
#   pi     -> pi_client (Raspberry Pi)
# The command to run is set per service in the compose files.
FROM python:3.14-slim

ARG DEPS_GROUP=server

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Installed via pip (not the ghcr.io/astral-sh/uv image) because that image has no
# linux/arm/v7 build, which 32-bit Raspberry Pi OS needs.
RUN pip install --no-cache-dir uv==0.13.6

# Dependencies first for better layer caching
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --group "$DEPS_GROUP"

# Application code (see .dockerignore)
COPY . .

CMD ["python", "entrypoints/bot.py"]
