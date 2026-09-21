.PHONY: install api web check backend-check frontend-check openspec-check integration

PNPM := cd frontend && pnpm

install:
	uv sync
	$(PNPM) install
	uv run pre-commit install

api:
	uv run uvicorn marketing_automation.api.main:app --reload --port 8000

web:
	$(PNPM) dev

backend-check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run lint-imports
	uv run pytest

frontend-check:
	$(PNPM) check

openspec-check:
	npx -y @fission-ai/openspec@1.13.1 validate --all --strict --no-interactive
	uv run python -m scripts.ci.check_openspec

integration:
	uv run pytest -m integration

check: backend-check frontend-check openspec-check
