# Application Layer - Use cases and business workflows

from src.domain.user import User
from src.infra.user_repository import UserRepository


class UserService:
    """Application service for user operations"""

    def __init__(self):
        self.repository = UserRepository()

    def create_user(self, user_id: str, name: str, email: str) -> User:
        """Create a new user"""
        user = User(user_id, name, email)

        if not user.validate_email():
            raise ValueError("Invalid email format")

        self.repository.save(user)
        return user

    def get_user(self, user_id: str) -> User:
        """Retrieve a user by ID"""
        return self.repository.find_by_id(user_id)
