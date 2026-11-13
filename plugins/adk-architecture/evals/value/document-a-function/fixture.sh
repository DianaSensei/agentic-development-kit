#!/usr/bin/env bash
# Documentation for one function. Measures what code-documenter adds: the why and the failure modes, in the file's existing style, without restating the obvious.
set -euo pipefail
mkdir -p src && cat > src/stock.py <<'PY'
class OutOfStock(Exception):
    pass


def available(sku):
    """Units of ``sku`` not yet reserved.

    :param sku: stock keeping unit
    :returns: a non-negative count
    """
    return LEVELS[sku] - RESERVED.get(sku, 0)


def reserve(sku, qty, ttl_seconds=900):
    if qty <= 0:
        raise ValueError("qty must be positive")
    if available(sku) < qty:
        raise OutOfStock(sku)
    RESERVED[sku] = RESERVED.get(sku, 0) + qty
    return ttl_seconds


LEVELS = {}
RESERVED = {}
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm init
