"""Legacy API handler with architectural violations.

This file demonstrates violations that would be tracked via baseline:
- Data layer importing from API (wrong direction)
- Direct coupling between layers
"""

# VIOLATION: This legacy code imports directly from API layer
# In clean architecture, data should not depend on API
from src.api.user_controller import UserController

# VIOLATION: Legacy code with tight coupling
from src.data.user_repository import UserRepository


class OldApiHandler:
    """Legacy handler that violates layering rules.

    This represents old code that was written before architectural
    guidelines were established. These violations are tracked via
    baseline so they don't block CI, but new code must not add
    similar violations.
    """

    def __init__(self) -> None:
        self._repo = UserRepository()
        # Bad: Legacy code creating controller directly
        self._controller = UserController(None)  # type: ignore

    def legacy_endpoint(self, user_id: str) -> dict:
        """Legacy endpoint mixing concerns."""
        # Direct repository access bypassing service layer
        user = self._repo.find_by_id(user_id)
        return user or {"error": "Not found"}
