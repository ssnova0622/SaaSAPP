### Where is the “Add to cart” option?

In the current project, adding items to a cart is done on the Carts page (admin UI), not on the Products list.

- Location: `admin_ui/src/pages/Store/Carts.tsx`
- UI label: “Store — Carts”
- What you’ll see:
  - A field to enter the customer phone number
  - An Items table with an “Add” button to add rows
  - Each row lets you enter `SKU`, `Qty`, and `Price`
  - Buttons to Save cart and Checkout

#### How to add to cart (current flow)
1. Open Store → Carts.
2. Enter the customer phone and click “Load” (loads or creates a cart for that phone).
3. Click “Add” to insert a new item row.
4. Fill in `SKU`, `Qty`, and `Price` (price is a snapshot; it does not auto-fill from product catalog yet).
5. Click “Save cart” to persist, or go to the right panel to “Checkout”.

Backend and API that power this:
- Router: `app/routers/store.py`
  - `GET /tenants/{tenant}/carts/{phone}` — fetch cart
  - `PUT /tenants/{tenant}/carts/{phone}` — save items
  - `POST /tenants/{tenant}/carts/{phone}/checkout` — checkout
- Client API: `admin_ui/src/api/store.ts` (`getCart`, `putCart`, `checkout`)

#### Why there isn’t an “Add to cart” button on Products
The Products page (`admin_ui/src/pages/Store/Products.tsx`) is an admin catalog manager (create/edit products, images, discount, stock). It isn’t a storefront or POS screen, so it doesn’t include “Add to cart” actions per product row.

#### Options to get per-product “Add to cart”
- Quick POS inside admin:
  - Add an “Add to cart” icon next to each product row in `Products.tsx` that opens a small dialog to pick quantity and pushes it into the active cart for a given phone.
  - Auto-fill `price_snapshot` from product `price` after applying `discount_type`/`discount_value` (same formula you already use in the product form preview).
- Separate Storefront page:
  - Create a new customer-facing page that lists products with images and an “Add to cart” button, maintains a cart context, then calls the same cart APIs to checkout.

If you tell me which direction you prefer (quick POS in admin vs. separate storefront), I can sketch the exact UI changes and wire them to the existing cart endpoints, including automatic price-from-SKU and discount handling so you don’t have to type price manually on the Carts page.