.PHONY: setup build test test-db lint api migrate poc schema

setup:
	uv sync --locked
	cargo build --locked -p zecsolve-verifier

build:
	cargo build --locked -p zecsolve-verifier

test: build
	cargo test --locked -p zecsolve-verifier
	uv run --locked pytest -m 'not postgres'

test-db:
	uv run --locked pytest -m postgres

lint:
	cargo fmt --all -- --check
	cargo clippy --locked -p zecsolve-verifier --all-targets -- -D warnings
	uv run --locked ruff check .
	uv run --locked ruff format --check .

api:
	uv run --locked uvicorn zecsolve.main:app --host 127.0.0.1 --port 8000 --no-access-log

migrate:
	uv run --locked alembic upgrade head

poc: build
	uv run --locked python scripts/poc.py

schema:
	uv run --locked python scripts/export_schema.py
