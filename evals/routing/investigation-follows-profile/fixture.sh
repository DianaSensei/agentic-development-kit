#!/usr/bin/env bash
# A cart bug - adding a product already in the cart overwrites its quantity instead
# of adding to it - and a profile whose Investigation section says how the user wants
# a cause traced and stated: user action -> flow -> API -> line, each with file:line,
# concluded in one fixed sentence. bug-fix must diagnose in that shape; a headless
# run can never confirm its Checkpoint, so a correct run edits nothing.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
git init -q
printf "profile/\n" > .git/info/exclude
mkdir -p src/shop tests
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest). HTTP handlers in api.py, logic in *_service.py.
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/api.py <<'PY'
from src.shop import cart_service

CARTS = {}


def post_cart_items(cart_id, body):
    """POST /carts/{cart_id}/items - the "Add to cart" button."""
    cart = CARTS.setdefault(cart_id, cart_service.Cart())
    cart_service.add_item(cart, body["sku"], int(body["qty"]))
    return {"lines": [{"sku": l.sku, "qty": l.qty} for l in cart.lines]}
PY
cat > src/shop/cart_service.py <<'PY'
from dataclasses import dataclass, field


@dataclass
class CartLine:
    sku: str
    qty: int


@dataclass
class Cart:
    lines: list = field(default_factory=list)


def add_item(cart, sku, qty):
    for line in cart.lines:
        if line.sku == sku:
            line.qty = qty
            return cart
    cart.lines.append(CartLine(sku, qty))
    return cart
PY
cat > tests/test_cart.py <<'PY'
from src.shop import cart_service


def test_add_new_item():
    cart = cart_service.add_item(cart_service.Cart(), "a", 2)
    assert [(l.sku, l.qty) for l in cart.lines] == [("a", 2)]
PY
git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Cart"
mkdir -p profile
cat > profile/profile.md <<'MD'
# How I work
<!-- A project's CLAUDE.md, REVIEW.md and checks override anything here. -->

## Investigation _(statement; 2026-11)_
- Trace the user's action -> flow -> API -> code, line by line; every link cites `file:line`.
- State the cause in one sentence: "Affects users who <action> on <flow>, via <API>, at `<file:line>`, because <cause>."
- A link without evidence is a hypothesis, marked as one.
MD
