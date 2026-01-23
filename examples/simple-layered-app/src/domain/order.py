# Domain Layer - Core business logic

from typing import List


class OrderItem:
    """An item in an order"""

    def __init__(self, product_id: str, quantity: int, price: float):
        self.product_id = product_id
        self.quantity = quantity
        self.price = price

    def total(self) -> float:
        return self.quantity * self.price


class Order:
    """Domain model for Order"""

    def __init__(self, order_id: str, user_id: str):
        self.order_id = order_id
        self.user_id = user_id
        self.items: List[OrderItem] = []

    def add_item(self, item: OrderItem) -> None:
        self.items.append(item)

    def calculate_total(self) -> float:
        return sum(item.total() for item in self.items)
