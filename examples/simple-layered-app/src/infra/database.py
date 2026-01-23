# Infrastructure Layer - Database connection

# ARCHITECTURAL VIOLATION: Infrastructure importing from domain
# This demonstrates a violation that Pacta will detect
from src.domain.user import User


class Database:
    """Mock database connection"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connected = False

    def connect(self) -> None:
        """Connect to database"""
        self.connected = True

    def disconnect(self) -> None:
        """Disconnect from database"""
        self.connected = False
