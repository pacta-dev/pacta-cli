from src.data.user_repository import UserRepository


class UserService:
    """Clean service with proper dependencies."""

    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def get_user(self, user_id: str) -> dict | None:
        """Get user by ID with business logic."""
        return self._repository.find_by_id(user_id)

    def create_user(self, name: str, email: str) -> dict:
        """Create a new user with validation."""
        if not name or not email:
            raise ValueError("Name and email are required")
        if "@" not in email:
            raise ValueError("Invalid email format")

        return self._repository.save({"name": name, "email": email})
