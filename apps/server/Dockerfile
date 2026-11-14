# Build from the repository root:
#   docker buildx build --platform linux/arm64 -f apps/server/Dockerfile .
#
# Staging runs on ARM64 Fargate, so the published image must be linux/arm64.
# The same image runs the API and the one-off tasks of the deploy workflow, which
# override the command: `alembic upgrade head`, the database seed, and the role setup.
# The seed needs Faker, so the image installs the `seed` dependency group.

ARG PYTHON_VERSION=3.13.5
ARG UV_VERSION=0.11.26

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app

# Install dependencies first so source edits do not invalidate this layer.
COPY apps/server/pyproject.toml apps/server/uv.lock ./
RUN --mount=type=cache,id=uv-cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group seed --no-install-project

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime
ENV PATH=/opt/venv/bin:${PATH} \
    PYTHONPATH=/app/src:/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SHIFU_SERVER_APP_PORT=7777
WORKDIR /app

RUN groupadd --system --gid 10001 shifu \
    && useradd --system --uid 10001 --gid shifu --home-dir /app --shell /usr/sbin/nologin shifu

COPY --from=build /opt/venv /opt/venv
COPY apps/server/alembic.ini ./alembic.ini
COPY apps/server/migrations ./migrations
COPY apps/server/src ./src

USER shifu
EXPOSE 7777

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('SHIFU_SERVER_APP_PORT', '7777') + '/health', timeout=4).status == 200 else 1)"

CMD ["python", "src/main.py"]
