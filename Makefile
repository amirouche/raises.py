.PHONY: init lock check check-with-coverage lint fmt typecheck

init:
	uv sync --group dev

lock:
	uv lock

check:
	uv run pytest

check-with-coverage:
	uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check raises.py

fmt:
	uv run ruff format raises.py

typecheck:
	uv run pyright raises.py
