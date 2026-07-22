.PHONY: install install-prod dev test lint type-check format format-check frontend-check check build \
	db-status db-upgrade db-backup db-restore docker-build docker-up docker-down \
	frontend-install frontend-dev frontend-build frontend-deploy

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

frontend-check:
	cd frontend && npx vue-tsc --noEmit

check: lint type-check format-check test frontend-check

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

frontend-install:
	cd frontend && npm install --silent

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-deploy: frontend-build
	rm -rf src/contract_guard/web
	mkdir -p src/contract_guard/web
	cp -r frontend/dist/* src/contract_guard/web/
