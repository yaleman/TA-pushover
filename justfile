# https://github.com/casey/just

# list things
default: list

# List the options
list:
    just --list


# Run all the checks
check: test lint mypy codespell

# Build the Splunk app package via UCC
build:
    ./ucc-build.sh

# Run ruff for linting
lint:
    uv run ruff check package tests
# Test Things
test:
    uv run pytest


# Optional end-to-end smoke test (requires ~/.config/ta-pushover.json)
test_e2e:
    uv run python app_test.py --send
