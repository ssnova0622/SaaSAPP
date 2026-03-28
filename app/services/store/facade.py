# app/services/store/facade.py
"""
Store facade: single entry point for store-related services. Reduces coupling
by grouping cart, products, inventory, checkout, and helpers behind one interface.
Use get_store_facade() in routers or other services instead of importing
each service separately.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.store.cart_service import CartService
from app.services.store.products_service import ProductService
from app.services.store.inventory_service import InventoryService
from app.services.store.categories_service import CategoryService
from app.services.store.orders_service import OrdersService
from app.services.store.checkout_service import CheckoutService
from app.services.store.offers_service import OffersService
from app.services.store.helpers.price_helper import PriceHelper
from app.services.store.helpers.unit_conversion_helper import UnitConversionHelper


class StoreFacade:
    """
    Facade over store services. Use this instead of importing
    CartService, ProductService, etc. directly when you need
    multiple store dependencies.
    """

    def __init__(self) -> None:
        self.cart = CartService
        self.products = ProductService
        self.inventory = InventoryService
        self.categories = CategoryService
        self.orders = OrdersService
        self.checkout = CheckoutService
        self.offers = OffersService
        self.price_helper = PriceHelper
        self.unit_conversion = UnitConversionHelper


_store_facade: Optional[StoreFacade] = None


def get_store_facade() -> StoreFacade:
    """Return the store facade singleton."""
    global _store_facade
    if _store_facade is None:
        _store_facade = StoreFacade()
    return _store_facade
