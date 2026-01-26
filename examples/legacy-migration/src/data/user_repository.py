import uuid


class UserRepository:
    """Clean repository implementation."""

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}

    def find_by_id(self, user_id: str) -> dict | None:
        """Find user by ID."""
        return self._users.get(user_id)

    def save(self, user: dict) -> dict:
        """Save a user."""
        if "id" not in user:
            user["id"] = str(uuid.uuid4())
        self._users[user["id"]] = user
        return user
