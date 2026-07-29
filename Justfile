# Install in editable mode
install:
    uv pip install -e .

# Install development dependencies
install-dev:
    uv sync --all-extras

# Lint code
lint:
    uv run ruff check --fix src/ tests/

# Format code
format:
    uv run ruff format src/ tests/

# Type check code
type:
    uv run ty check src/ tests/

# Check code quality
check:
    uv run ruff check src/ tests/
    uv run ruff format src/ tests/
    uv run ty check src/ tests/

# Run all tests
test:
    uv run pytest tests/ -v

# Run all tests with coverage
test-cov:
    uv run pytest tests/ --cov=src --cov-report=html --cov-report=term

# Run pre-commit checks
pre:
    uv run prek run --all-files

# Start application shell
run:
    uv run python -m src.app.shell

# Build the calendars and the static site into public/
build-site:
    uv run scripts/build_calendars.py
    node scripts/build_site.js

# Serve the built site
serve: build-site
    uv run python -m http.server -d public 8000

# Generate overrides template
overrides:
    uv run python -m scripts.make_overrides_template

# Update the team cache
cache:
    uv run python -m scripts.cache

# Clean up temporary files
clean:
    uv run python -m scripts.clean
