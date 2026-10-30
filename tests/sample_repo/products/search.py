"""Product search and catalog filtering."""

from typing import List, Optional
from products.catalog import Product, ProductCatalog


def search_products(
    catalog: ProductCatalog,
    query: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[Product]:
    """Search products by keyword in name and description with price filtering."""
    q_lower = query.strip().lower()
    results: List[Product] = []

    for product in catalog.list_products():
        # Check price bounds
        if min_price is not None and product.price < min_price:
            continue
        if max_price is not None and product.price > max_price:
            continue

        # Check keyword in name or description
        if q_lower in product.name.lower() or q_lower in product.description.lower():
            results.append(product)

    return results
