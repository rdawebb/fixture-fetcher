# Justfile for fixture-fetcher

help:
    @printf "\nAvailable commands:\n\n  just install      - Install dependencies\n  just install-dev  - Install dependencies + dev tools\n  just lint         - Run ruff linter\n  just format       - Format code with ruff\n  just type         - Run ty type checker\n  just check        - Run all checks\n  just test         - Run tests\n  just test-cov     - Run tests with coverage report\n  just run          - Run the CLI app\n  just overrides    - Generate overrides template\n  just cache        - Update the team cache\n  just clean        - Remove cache and temporary files\n\n"

install:
    uv pip install -e .

install-dev:
    uv sync --all-extras

lint:
    uv run ruff check --fix src/ tests/

format:
    uv run ruff format src/ tests/

type:
    uv run ty check src/ tests/

check:
    uv run ruff check src/ tests/
    uv run ruff format src/ tests/
    uv run ty check src/ tests/

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
