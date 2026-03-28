"""
Store-module constants only. Use for order/payment status strings and store-specific values.
Do not put other modules' constants here. Shared capability names live in app.constants.
"""
from __future__ import annotations

# Payment status (orders)
PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_PAID = "paid"
PAYMENT_STATUS_FAILED = "failed"

# Order status
ORDER_STATUS_CANCELED = "canceled"

# Payment method
PAYMENT_METHOD_COD = "COD"
PAYMENT_METHOD_ONLINE = "ONLINE"
