### Fix applied for number-based actions + how to validate with your menu
I addressed the issue where selecting a number in WhatsApp did not trigger the expected action. Your example menu has `menu_id = "welcome menu"` and option 1 points to the `Offers` action node (show_offers). The webhook used to always load `default` — now it resolves the correct active menu automatically and reliably executes the action pointed by the selected option.

#### What I changed (server)
- Active menu resolution (not always “default”)
  - The webhook now selects the active published menu in this order:
    1) `tenant.whatsapp_config.active_menu_id` if set and published
    2) Published menu with `menu_id = "default"` if exists
    3) Otherwise, the latest published menu across all menu_ids (highest version)
  - This means your published menu `welcome menu` (v11) will be used automatically if it’s the latest.
- Robust numeric choice parsing
  - Inputs like `1`, `1)`, `1.`, `1 - book`, or `  2  ` are parsed to the key (e.g., `1`, `2`).
- Action execution from submenu options
  - When a submenu option’s `next` points to an action node (like your `Offers` node with `show_offers`), the webhook checks `requires_caps` and then executes the action.
- Lightweight session
  - We remember the caller’s last submenu so the next numeric reply is evaluated in that submenu context. After executing an action, session resets to root.

#### Why your case should work now
Your published menu (v11) root options:
- key `1` → next `Offers` → node id `Offers` is an action node `show_offers`
- The webhook now loads `welcome menu` (due to newest published version), finds `root`, parses `Body: "1"` to key `1`, follows `next: "Offers"`, and runs `show_offers`.

#### How to test quickly (without Twilio)
Use the dummy webhook:
```
POST /v1/integrations/twilio/whatsapp/webhook
Content-Type: application/json

{ "From": "+911112223334", "To": "whatsapp:+14155238886", "Body": "1" }
```
Expected: TwiML XML response with the “offers” reply (from `show_offers`).

Try also:
- `Body: "1)"` or `Body: "1 - book"` → still treated as key `1` and should run `Offers`.

#### Optional: explicitly set the active menu (if you have multiple published menus)
You can set a preferred menu id in tenant config under `whatsapp_config.active_menu_id` to force which published menu is used. If not set, the latest published menu is picked automatically as above.

#### If you still don’t see the action reply
Please check these items and share the outputs if it persists:
- Does the webhook response say “Invalid choice”?
  - Ensure the option key in `root.options` is exactly the string you send (e.g., `"1"`).
- Does it say “Menu is invalid”?
  - Verify the `next` value (`"Offers"`) matches a node id exactly (IDs are case-sensitive). Your node id is `Offers`, which matches your `next` value.
- Does it say “This option is not available for this tenant.”?
  - Then the action node has `requires_caps` that are not enabled for the tenant. Enable the capability in Super Admin → Settings → Modules & Capabilities.
- Is your `To` number configured in the tenant config? It should be saved as `whatsapp:+14155238886`. The resolver now also accepts `+14155238886` from Twilio payloads.

If you share the latest webhook response (status + body) after sending `Body: "1"`, I can pinpoint immediately (node match vs capability vs menu resolution). But with the latest change, your `welcome menu` → `1` → `Offers` → `show_offers` should work out of the box.