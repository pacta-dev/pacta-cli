from src.services.user_service import UserService


class UserController:
    """Clean API controller following proper layering."""

    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def get_user(self, user_id: str) -> dict:
        """GET /users/{id}"""
        user = self._user_service.get_user(user_id)
        if not user:
            return {"error": "User not found"}
        return {"id": user["id"], "name": user["name"], "email": user["email"]}

    def create_user(self, name: str, email: str) -> dict:
        """POST /users"""
        user = self._user_service.create_user(name, email)
        return {"id": user["id"], "name": user["name"]}
