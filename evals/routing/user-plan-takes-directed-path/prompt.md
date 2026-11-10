Add a loyalty discount. Do exactly these steps, in this order:
1. In `src/shop/orders.py`, add `loyalty_points: int = 0` to `Order`.
2. Add `Order.discount()`: 1.00 off for every full 100 points, capped at 10% of the subtotal.
3. `Order.total()` subtracts `discount()` from the subtotal.
4. In `src/shop/receipt.py`, add a line `Loyalty  -<discount>` above the total, only when the discount is above zero.
5. Add tests for the cap and for the receipt line to `tests/test_orders.py`.
