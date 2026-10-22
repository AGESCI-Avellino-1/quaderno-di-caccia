# syntax=docker/dockerfile:1
# QdC backend: Django + gunicorn. Built by compose.prod.yml (see README, "Produzione").

FROM python:3.14-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY . .
# collectstatic needs no database nor real secrets.
RUN DJANGO_SETTINGS_MODULE=config.settings.base DJANGO_SECRET_KEY=collectstatic-only \
    /opt/venv/bin/python manage.py collectstatic --noinput

FROM python:3.14-slim
RUN groupadd --system qdc && useradd --system --gid qdc --home-dir /app qdc \
    && mkdir -p /data/media && chown qdc:qdc /data/media
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    QDC_MEDIA_ROOT=/data/media \
    GUNICORN_CMD_ARGS="--workers 3 --access-logfile -"
COPY --from=build /opt/venv /opt/venv
COPY --from=build --chown=qdc:qdc /app /app
WORKDIR /app
USER qdc
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000"]
