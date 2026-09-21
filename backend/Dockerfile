# Platform API image. Build from the repo root:
#   docker build -f backend/Dockerfile -t marketing-automation-api .
FROM python:3.11-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first for layer caching.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend ./backend
COPY skills ./skills
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 app
USER app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "marketing_automation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
