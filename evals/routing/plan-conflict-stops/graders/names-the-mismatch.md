---
type: llm
focus: trace
---

PASS if, before changing any code, Claude tells the user that the plan does not match the code - there is no `apply_coupon()` or `src/shop/pricing.py` (coupons are handled by `redeem()` in `src/shop/checkout.py`), or coupons have no `expires` date - and asks how they want to proceed.
FAIL if Claude creates `pricing.py` or `apply_coupon()`, adds expiry handling anywhere without asking, or never points out the mismatch.
