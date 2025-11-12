.PHONY: help install install-dev lint format type-check test run clean overrides

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make install-dev  - Install dependencies + dev tools"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Run mypy type checking"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make run          - Run the CLI app"
	@echo "  make overrides    - Generate overrides template"
	@echo "  make clean        - Remove cache and temporary files"

install:
	uv pip install -r requirements.txt

install-dev:
	uv pip install -r requirements.txt[dev]

lint:
	ruff check src/ --show-fixes

format:
	ruff format src/

type-check:
	mypy src/

check: lint type-check
	@echo "✓ All checks passed!"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

run:
	python3 -m src.cli build --help

overrides:
	python3 -m scripts.make_overrides_template

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Cache cleaned!"
