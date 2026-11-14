.PHONY: install dev lint format type check test test-coverage docker-up docker-down db-migrate db-upgrade db-downgrade db-current db-sync

install:
	python3 -m venv venv
	venv/bin/pip install -r requirements.txt

dev:
	venv/bin/uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

lint:
	venv/bin/ruff check src/ tests/ scripts/

format:
	venv/bin/ruff format src/ tests/ scripts/

type:
	venv/bin/mypy src/

check:
	venv/bin/ruff check src/ tests/ scripts/ && venv/bin/ruff format --check src/ tests/ scripts/ && venv/bin/mypy src/

test:
	PYTHONPATH=. venv/bin/pytest

test-coverage:
	PYTHONPATH=. venv/bin/pytest --cov=src --cov-report=term-missing

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Database migrations (Alembic)
db-migrate:
	@echo "Generating migration: $(if $(MSG),$(MSG),auto)"
	PYTHONPATH=. venv/bin/alembic revision --autogenerate -m "$(if $(MSG),$(MSG),auto)"

db-upgrade:
	PYTHONPATH=. venv/bin/alembic upgrade head

db-downgrade:
	PYTHONPATH=. venv/bin/alembic downgrade -1

db-current:
	PYTHONPATH=. venv/bin/alembic current

db-sync:
	PYTHONPATH=. python -c "\
import asyncio; \
from src.infrastructure.persistence.session import get_engine; \
from src.infrastructure.persistence.models.base import Base; \
async def sync(): \
    engine = get_engine(); \
    async with engine.begin() as conn: \
        await conn.run_sync(Base.metadata.create_all); \
    await engine.dispose(); \
asyncio.run(sync())"
