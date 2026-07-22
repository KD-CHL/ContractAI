.PHONY: install install-prod dev test lint type-check format format-check js-check check build \
	db-status db-upgrade db-backup db-restore docker-build docker-up docker-down

PYTHON ?= python3.12
VENV ?= .venv
PIP := $(VENV)/bin/python -m pip
PYTEST := $(VENV)/bin/python -m pytest
RUFF := $(VENV)/bin/python -m ruff
MYPY := $(VENV)/bin/python -m mypy
DB ?= data/contractguard.db
BACKUP ?=

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip 'setuptools>=75,<82' 'wheel>=0.45,<1'
	$(PIP) install -e '.[dev]'

install-prod:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip 'setuptools>=75,<82' 'wheel>=0.45,<1'
	$(PIP) install '.[prod]'

dev:
	$(VENV)/bin/python -m uvicorn contract_guard.main:app --reload --host $${HOST:-0.0.0.0} --port $${PORT:-8010} --log-level $${LOG_LEVEL:-info}

test:
	$(PYTEST)

lint:
	$(RUFF) check src tests

type-check:
	$(MYPY) src

format-check:
	$(RUFF) format --check src tests

format:
	$(RUFF) format src tests
	$(RUFF) check --fix src tests

js-check:
	node --check src/contract_guard/web/app.js

check: lint type-check format-check test js-check

build:
	$(PIP) wheel --no-build-isolation --no-deps --wheel-dir dist .

db-status:
	$(VENV)/bin/python scripts/manage_db.py status --database "$(DB)"

db-upgrade:
	$(VENV)/bin/python scripts/manage_db.py upgrade --database "$(DB)"

db-backup:
	@test -n "$(BACKUP)" || (echo "Usage: make db-backup BACKUP=backups/pre-release.db"; exit 2)
	$(VENV)/bin/python scripts/manage_db.py backup --database "$(DB)" --destination "$(BACKUP)"

db-restore:
	@test -n "$(BACKUP)" || (echo "Usage: make db-restore BACKUP=backups/pre-release.db"; exit 2)
	$(VENV)/bin/python scripts/manage_db.py restore --backup "$(BACKUP)" --destination "$(DB)"

docker-build:
	docker build -t contractguard:local .

docker-up:
	docker compose up --build

docker-down:
	docker compose down
