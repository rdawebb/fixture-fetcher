# Justfile for fixture-fetcher

help:
    @echo "Available commands:"
    @echo "  just install      - Install dependencies"
    @echo "  just install-dev  - Install dependencies + dev tools"
    @echo "  just lint         - Run ruff linter"
    @echo "  just format       - Format code with ruff"
    @echo "  just test         - Run tests"
    @echo "  just test-cov     - Run tests with coverage report"
    @echo "  just run          - Run the CLI app"
    @echo "  just overrides    - Generate overrides template"
    @echo "  just cache        - Update the team cache"
    @echo "  just clean        - Remove cache and temporary files"

install:
    uv pip install .

install-dev:
    uv sync --all-extras

lint:
    ruff check src/ --show-fixes

format:
    ruff format src/

test:
    uv run pytest tests/ -v

test-cov:
    uv run pytest tests/ --cov=src --cov-report=html --cov-report=term

run:
    uv run python -m src.app.shell

overrides:
    uv run python -m scripts.make_overrides_template

cache:
    uv run python -m scripts.cache

clean:
    uv run python -m scripts.clean