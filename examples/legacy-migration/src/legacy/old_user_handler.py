"""Legacy user handler - gradually being migrated.

This file contains architectural violations that are tracked via baseline.
New code should not depend on this module.
"""

# GOOD: Legacy code using new services (migration in progress)
from src.services.user_service import UserService

# GOOD: Legacy code using new data layer
from src.data.user_repository import UserRepository


class OldUserHandler:
    """Legacy handler being migrated to clean architecture.

    This class mixes concerns and will be refactored into:
    - UserController (API layer)
    - UserService (Service layer)
    """

    def __init__(self) -> None:
        # Legacy: direct instantiation instead of dependency injection
        self._repository = UserRepository()
        self._service = UserService(self._repository)

    def handle_request(self, action: str, data: dict) -> dict:
        """Handle user requests (legacy catch-all method)."""
        if action == "get":
            return self._get_user(data.get("id", ""))
        elif action == "create":
            return self._create_user(data)
        else:
            return {"error": f"Unknown action: {action}"}

    def _get_user(self, user_id: str) -> dict:
        """Get user - delegates to new service."""
        user = self._service.get_user(user_id)
        return user or {"error": "Not found"}

    def _create_user(self, data: dict) -> dict:
        """Create user - delegates to new service."""
        try:
            return self._service.create_user(
                name=data.get("name", ""),
                email=data.get("email", ""),
            )
        except ValueError as e:
            return {"error": str(e)}
