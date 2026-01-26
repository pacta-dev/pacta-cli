from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Product:
    """Domain entity representing a product."""

    id: str
    name: str
    price: Decimal
    stock: int

    def is_available(self) -> bool:
        """Check if product is in stock."""
        return self.stock > 0

    def reduce_stock(self, quantity: int) -> None:
        """Reduce stock after a purchase."""
        if quantity > self.stock:
            raise ValueError(f"Insufficient stock: requested {quantity}, available {self.stock}")
        self.stock -= quantity
