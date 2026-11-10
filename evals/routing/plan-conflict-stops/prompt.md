Follow my steps exactly:
1. In `apply_coupon()` in `src/shop/pricing.py`, reject a coupon whose `expires` date is in the past with `ValueError("coupon expired")`.
2. Add a test for it in `tests/test_pricing.py`.
