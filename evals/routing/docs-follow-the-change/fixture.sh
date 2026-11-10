#!/usr/bin/env bash
# A one-line change whose value the README states: the product listing's page size.
# Changing the constant alone leaves the README wrong; the self-review's "the docs are
# still true" check must catch it and update the README in the same change.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/shop tests
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest).
MD
cat > README.md <<'MD'
# Shop

## Product listing

`GET /products?page=N` returns 20 products per page (`PAGE_SIZE` in `src/shop/catalog.py`), newest first.
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/catalog.py <<'PY'
PAGE_SIZE = 20


def page(products, n):
    start = (n - 1) * PAGE_SIZE
    return products[start:start + PAGE_SIZE]
PY
cat > tests/test_catalog.py <<'PY'
from src.shop.catalog import PAGE_SIZE, page


def test_first_page_is_full():
    assert len(page(list(range(200)), 1)) == PAGE_SIZE
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Catalog"
