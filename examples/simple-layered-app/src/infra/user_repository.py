# Infrastructure Layer - Data persistence

# VIOLATION: Domain layer should not depend on infrastructure
# This is intentionally importing from domain to demonstrate rule detection
from src.domain.user import User


class UserRepository:
    """Repository for persisting users"""

    def __init__(self):
        self.users = {}

    def save(self, user: User) -> None:
        """Save a user to the database"""
        self.users[user.user_id] = user

    def find_by_id(self, user_id: str) -> User:
        """Find a user by ID"""
        if user_id not in self.users:
            raise ValueError(f"User {user_id} not found")
        return self.users[user_id]
