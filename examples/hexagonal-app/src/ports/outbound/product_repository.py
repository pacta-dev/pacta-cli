from abc import ABC, abstractmethod

from src.domain.product import Product


class ProductRepository(ABC):
    """Outbound port for product persistence.

    This interface is defined in the ports layer and implemented
    by secondary adapters (e.g., PostgresProductRepository).
    The domain uses this interface without knowing the implementation.
    """

    @abstractmethod
    def find_by_id(self, product_id: str) -> Product | None:
        """Find a product by its ID."""
        ...

    @abstractmethod
    def find_all(self) -> list[Product]:
        """Find all products."""
        ...

    @abstractmethod
    def find_available(self) -> list[Product]:
        """Find all products that are in stock."""
        ...

    @abstractmethod
    def save(self, product: Product) -> Product:
        """Save a product (create or update)."""
        ...
