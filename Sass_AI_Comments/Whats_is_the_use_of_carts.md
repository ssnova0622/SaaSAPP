### What is the use of a cart in a store app?

A cart (shopping cart) lets a customer collect one or more products they intend to purchase, review quantities and prices (including discounts/taxes), and then proceed to checkout and payment. It’s the bridge between browsing products and placing an order.

#### Why carts are useful
- Collect items: Add multiple SKUs with chosen quantities before paying.
- Price transparency: Show item price, discounts (amount/percent), taxes, and the running subtotal/total.
- Edit before buying: Change quantities, remove items, or save for later.
- Multi‑step checkout: Capture shipping/billing info, delivery options, and payment.
- Promotions: Apply coupons or automatic discounts at cart level (e.g., buy 2 get 1).
- Conversion & analytics: Measure cart abandonment and optimize funnels.
- Inventory sanity: Optionally reserve stock temporarily during checkout to reduce overselling.

#### How a cart fits your current project
You already have:
- Products with price, tax, unit, optional image, and discounts (amount/percent).
- Inventory endpoints (`getInventory`, `setInventory`).

A cart would consume these and produce orders. Typical flow:
1. Browse products → add to cart (SKU + quantity).
2. Cart view → displays item details, discount-adjusted line totals, tax, subtotal, total.
3. Checkout → collect address/contact, choose delivery/pickup, confirm.
4. Payment → on success, create an order, decrement inventory, clear cart.

#### Basic data model (example)
- Cart
  - `id` (or `cart_token` for guests)
  - `tenant`
  - `user_id` (nullable for guest carts)
  - `currency`
  - `items`: list of cart items
  - `prices`: `subtotal`, `discount_total`, `tax_total`, `shipping_total`, `grand_total`
  - `status`: `active | converted | abandoned`
  - `updated_at`
- CartItem
  - `sku`, `name`, `image_url`
  - `qty`
  - `unit_price` (snapshot of product price)
  - `discount_type` (`amount|percent|null`) and `discount_value`
  - `final_price` per unit (after discount)
  - `line_total` (= `qty * final_price`)

This mirrors your existing product fields so pricing stays consistent.

#### Minimal API surface (tenant‑scoped)
- `POST /tenants/{tenant}/cart` → create/get cart (for guest returns a token)
- `POST /tenants/{tenant}/cart/items` → add or increase `sku`, `qty`
- `PUT /tenants/{tenant}/cart/items/{sku}` → update quantity
- `DELETE /tenants/{tenant}/cart/items/{sku}` → remove item
- `GET /tenants/{tenant}/cart` → fetch current cart
- `POST /tenants/{tenant}/cart/checkout` → validate stock/prices, create order, decrement inventory

Optional:
- `POST /tenants/{tenant}/cart/apply-coupon` → apply a promo code
- `POST /tenants/{tenant}/cart/reserve` → temporary inventory reservation during payment

#### Pricing logic (aligned with your discount fields)
- If `discount_type = amount`: `final_price = max(0, price - discount_value)`
- If `discount_type = percent`: `final_price = max(0, price - price*(discount_value/100))`
- Else: `final_price = price`
- Line total: `qty * final_price`
- Add per‑item tax if you treat `tax` as percent: `tax_total += line_total * (tax/100)`

#### Inventory considerations
- Soft hold: Optionally reserve stock (e.g., for 10–15 minutes) once the customer starts checkout; release on timeout or failure.
- Hard decrement: On order success, call your existing `setInventory` to reduce available quantity.

#### UX expectations
- Cart icon with item count
- Slide‑out or dedicated page showing:
  - Items with images, unit price, discount, qty controls, line totals
  - Subtotals, tax, shipping (if any), grand total
  - Checkout button

#### Multi‑tenant note
Since your platform is tenant‑scoped, each cart must be tied to a single `tenant` and should not mix items from different tenants.

---
If you’d like, I can outline the exact endpoints and a simple React cart context to integrate with your current `admin_ui` and backend, or implement a minimal MVP (guest cart + checkout) next.