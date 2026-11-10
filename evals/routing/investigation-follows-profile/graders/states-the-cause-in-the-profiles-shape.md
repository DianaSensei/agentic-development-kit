---
type: llm
focus: trace
---

PASS if Claude states the cause in the profile's sentence - "Affects users who <action> on <flow>, via <API>, at <file:line>, because <cause>" - naming adding a product already in the cart, the `POST /carts/{cart_id}/items` handler (`post_cart_items`), and the line in `src/shop/cart_service.py` where the quantity is overwritten instead of added; and traces the chain from the user's action to that line with a `file:line` for each link.
FAIL if the cause is stated without that sentence or without `file:line` evidence, or if Claude changed code in `src/`.
