# Domain Layer - Core business logic

class User:
    """Domain model for User"""

    def __init__(self, user_id: str, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email

    def validate_email(self) -> bool:
        """Validate email format"""
        return "@" in self.email and "." in self.email.split("@")[1]
