"""Product catalog repository and retrieval services."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Product:
    """Represents a merchandise item in the store."""
    id: str
    name: str
    description: str
    price: float
    category: str
    in_stock: bool = True


class ProductCatalog:
    """In-memory merchandise catalog with CRUD operations."""

    def __init__(self):
        self._items: Dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        """Add a new product to the catalog."""
        self._items[product.id] = product

    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Fetch a single product by unique identifier."""
        return self._items.get(product_id)

    def list_products(self, category: Optional[str] = None) -> List[Product]:
        """List all available products, optionally filtered by category."""
        if category:
            return [p for p in self._items.values() if p.category.lower() == category.lower()]
        return list(self._items.values())
