# services/ai/helpers/inventory_utils.py

from typing import Dict, List
from app.helpers.tools import to_float


def get_inventory_map(tenant: str, skus: List[str], inventory_repo) -> Dict[str, float]:
    """
    Return a map of SKU → available_qty.
    """
    if not skus:
        return {}

    inv_map: Dict[str, float] = {}
    for inv in inventory_repo.find_by_skus(tenant, skus):
        inv_map[str(inv.sku)] = to_float(inv.available_qty)

    return inv_map
