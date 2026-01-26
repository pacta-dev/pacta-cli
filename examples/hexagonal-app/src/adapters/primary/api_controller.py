from dataclasses import dataclass
from decimal import Decimal

from src.ports.inbound.catalog_use_case import CatalogUseCase


@dataclass
class ProductDTO:
    """Data Transfer Object for API responses."""

    id: str
    name: str
    price: str
    available: bool


class ProductController:
    """Primary adapter - REST API controller.

    This adapter receives HTTP requests and translates them to
    use case calls via the inbound port (CatalogUseCase).
    """

    def __init__(self, catalog: CatalogUseCase) -> None:
        self._catalog = catalog

    def get_product(self, product_id: str) -> ProductDTO | None:
        """GET /products/{id}"""
        product = self._catalog.get_product(product_id)
        if not product:
            return None
        return ProductDTO(
            id=product.id,
            name=product.name,
            price=str(product.price),
            available=product.is_available(),
        )

    def list_products(self) -> list[ProductDTO]:
        """GET /products"""
        products = self._catalog.list_available_products()
        return [
            ProductDTO(
                id=p.id,
                name=p.name,
                price=str(p.price),
                available=p.is_available(),
            )
            for p in products
        ]

    def update_price(self, product_id: str, new_price: str) -> ProductDTO:
        """PATCH /products/{id}/price"""
        product = self._catalog.update_product_price(product_id, Decimal(new_price))
        return ProductDTO(
            id=product.id,
            name=product.name,
            price=str(product.price),
            available=product.is_available(),
        )
