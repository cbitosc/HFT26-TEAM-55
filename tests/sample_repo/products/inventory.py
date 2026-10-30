"""Inventory management and warehouse stock reservation."""

from typing import Dict

# product_id -> available stock quantity
_STOCK_LEVELS: Dict[str, int] = {}
# order_id -> {product_id: reserved_qty}
_RESERVATIONS: Dict[str, Dict[str, int]] = {}


def check_stock(product_id: str) -> int:
    """Return the available quantity for a product."""
    return _STOCK_LEVELS.get(product_id, 0)


def reserve_stock(order_id: str, product_id: str, quantity: int) -> bool:
    """Temporarily reserve inventory units for an active checkout session."""
    current = check_stock(product_id)
    if current < quantity:
        return False

    _STOCK_LEVELS[product_id] = current - quantity
    if order_id not in _RESERVATIONS:
        _RESERVATIONS[order_id] = {}
    _RESERVATIONS[order_id][product_id] = _RESERVATIONS[order_id].get(product_id, 0) + quantity
    return True


def release_reserved_stock(order_id: str) -> None:
    """Release reserved stock back into available inventory if checkout is cancelled."""
    if order_id in _RESERVATIONS:
        for pid, qty in _RESERVATIONS[order_id].items():
            _STOCK_LEVELS[pid] = _STOCK_LEVELS.get(pid, 0) + qty
        del _RESERVATIONS[order_id]


def update_inventory(product_id: str, new_quantity: int) -> None:
    """Restock or adjust inventory level for a product."""
    _STOCK_LEVELS[product_id] = max(0, new_quantity)
