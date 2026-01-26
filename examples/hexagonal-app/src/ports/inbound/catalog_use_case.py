from abc import ABC, abstractmethod
from decimal import Decimal

from src.domain.product import Product


class CatalogUseCase(ABC):
    """Inbound port defining catalog operations.

    This is the use case interface that primary adapters (controllers, CLI)
    will use to interact with the application.
    """

    @abstractmethod
    def get_product(self, product_id: str) -> Product | None:
        """Get a product by its ID."""
        ...

    @abstractmethod
    def list_available_products(self) -> list[Product]:
        """List all products that are in stock."""
        ...

    @abstractmethod
    def update_product_price(self, product_id: str, new_price: Decimal) -> Product:
        """Update the price of a product."""
        ...
