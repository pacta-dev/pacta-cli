from decimal import Decimal

from src.domain.product import Product
from src.ports.outbound.product_repository import ProductRepository


class ProductService:
    """Domain service for product operations.

    Uses outbound port (ProductRepository) via dependency injection.
    """

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def get_product(self, product_id: str) -> Product | None:
        """Get a product by ID."""
        return self._repository.find_by_id(product_id)

    def update_price(self, product_id: str, new_price: Decimal) -> Product:
        """Update product price with business validation."""
        if new_price <= 0:
            raise ValueError("Price must be positive")

        product = self._repository.find_by_id(product_id)
        if not product:
            raise ValueError(f"Product not found: {product_id}")

        product.price = new_price
        return self._repository.save(product)
