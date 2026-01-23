# Application Layer - Use cases and business workflows

from src.domain.order import Order, OrderItem
from src.infra.order_repository import OrderRepository
from src.ui.order_controller import OrderController


class OrderService:
    """Application service for order operations"""

    def __init__(self):
        self.repository = OrderRepository()

    def create_order(self, order_id: str, user_id: str) -> Order:
        """Create a new order"""
        order = Order(order_id, user_id)
        self.repository.save(order)
        return order

    def add_item_to_order(self, order_id: str, product_id: str, quantity: int, price: float) -> None:
        """Add an item to an existing order"""
        order = self.repository.find_by_id(order_id)
        item = OrderItem(product_id, quantity, price)
        order.add_item(item)
        self.repository.save(order)

    def get_order_total(self, order_id: str) -> float:
        """Get the total amount for an order"""
        order = self.repository.find_by_id(order_id)
        return order.calculate_total()
