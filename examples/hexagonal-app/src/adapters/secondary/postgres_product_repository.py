from decimal import Decimal

from src.domain.product import Product
from src.ports.outbound.product_repository import ProductRepository


class PostgresProductRepository(ProductRepository):
    """Secondary adapter - PostgreSQL implementation of ProductRepository.

    This adapter implements the outbound port (ProductRepository) and
    handles the actual database operations.
    """

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string
        # In a real app, this would initialize a database connection
        self._products: dict[str, Product] = {}

    def find_by_id(self, product_id: str) -> Product | None:
        """Find a product by ID from the database."""
        # Simulated database query
        return self._products.get(product_id)

    def find_all(self) -> list[Product]:
        """Find all products from the database."""
        return list(self._products.values())

    def find_available(self) -> list[Product]:
        """Find all available products from the database."""
        return [p for p in self._products.values() if p.is_available()]

    def save(self, product: Product) -> Product:
        """Save a product to the database."""
        # Simulated database save
        self._products[product.id] = product
        return product

    def seed_data(self) -> None:
        """Seed initial data for testing."""
        self._products = {
            "1": Product(id="1", name="Widget", price=Decimal("19.99"), stock=100),
            "2": Product(id="2", name="Gadget", price=Decimal("49.99"), stock=50),
            "3": Product(id="3", name="Gizmo", price=Decimal("29.99"), stock=0),
        }
