# UI/API Layer - HTTP endpoints

from src.application.user_service import UserService

# VIOLATION: UI layer should not directly access infrastructure
# This is an architectural violation that Pacta will catch
from src.infra.database import Database


class UserController:
    """REST API controller for user endpoints"""

    def __init__(self):
        self.service = UserService()
        # VIOLATION: Direct database access from UI layer
        self.db = Database("postgresql://localhost:5432/myapp")

    def create_user_endpoint(self, request_data: dict) -> dict:
        """POST /users endpoint"""
        user = self.service.create_user(
            user_id=request_data["id"],
            name=request_data["name"],
            email=request_data["email"]
        )
        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email
        }

    def get_user_endpoint(self, user_id: str) -> dict:
        """GET /users/{id} endpoint"""
        user = self.service.get_user(user_id)
        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email
        }
