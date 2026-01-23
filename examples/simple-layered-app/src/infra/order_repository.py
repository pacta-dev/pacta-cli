# Infrastructure Layer - Data persistence

from src.domain.order import Order


class OrderRepository:
    """Repository for persisting orders"""

    def __init__(self):
        self.orders = {}

    def save(self, order: Order) -> None:
        """Save an order to the database"""
        self.orders[order.order_id] = order

    def find_by_id(self, order_id: str) -> Order:
        """Find an order by ID"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        return self.orders[order_id]
