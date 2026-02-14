FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic/ alembic/
COPY shelflife/ shelflife/
RUN uv sync --no-dev

EXPOSE 8000

ARG MODE=api
ENV SHELFLIFE_MODE=${MODE}

CMD ["sh", "-c", \
    "if [ \"$SHELFLIFE_MODE\" = \"mcp\" ]; then \
        uv run python -m shelflife.mcp; \
    else \
        uv run alembic upgrade head && uv run uvicorn shelflife.app:app --host 0.0.0.0 --port 8000; \
    fi"]
