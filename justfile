# https://github.com/casey/just

# list things
default: list

# List the options
list:
    just --list


# Run all the checks
check: test lint mypy codespell

# Run ruff for linting
lint:
    uv run ruff check package tests
# Test Things
test:
    uv run pytest
# Run mypy
mypy:
    find ./package/ -type f -name '*.py' -exec uv run  mypy --strict "{}" \;
    uv run mypy --strict tests/

# Spell check the things
codespell:
    codespell -c \
    --ignore-words .codespell_ignore \
    --skip='./layer_ghapi' \
    --skip='./.venv' \

# Semgrep things
semgrep:
    semgrep ci --config auto \
    --exclude-rule "yaml.github-actions.security.third-party-action-not-pinned-to-commit-sha.third-party-action-not-pinned-to-commit-sha" \
    --exclude-rule "generic.html-templates.security.var-in-script-tag.var-in-script-tag" \
    --exclude-rule "javascript.express.security.audit.xss.mustache.var-in-href.var-in-href" \
    --exclude-rule "python.django.security.django-no-csrf-token.django-no-csrf-token" \
    --exclude-rule "python.django.security.audit.xss.template-href-var.template-href-var" \
    --exclude-rule "python.django.security.audit.xss.var-in-script-tag.var-in-script-tag" \
    --exclude-rule "python.flask.security.xss.audit.template-href-var.template-href-var" \
    --exclude-rule "python.flask.security.xss.audit.template-href-var.template-href-var"

run_splunk:
    docker compose up -d
    docker compose logs -f