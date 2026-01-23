# UI/API Layer - HTTP endpoints

from src.application.order_service import OrderService


class OrderController:
    """REST API controller for order endpoints"""

    def __init__(self):
        self.service = OrderService()

    def create_order_endpoint(self, request_data: dict) -> dict:
        """POST /orders endpoint"""
        order = self.service.create_order(
            order_id=request_data["order_id"],
            user_id=request_data["user_id"]
        )
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "items": []
        }

    def add_item_endpoint(self, order_id: str, request_data: dict) -> dict:
        """POST /orders/{id}/items endpoint"""
        self.service.add_item_to_order(
            order_id=order_id,
            product_id=request_data["product_id"],
            quantity=request_data["quantity"],
            price=request_data["price"]
        )
        total = self.service.get_order_total(order_id)
        return {
            "order_id": order_id,
            "total": total
        }
