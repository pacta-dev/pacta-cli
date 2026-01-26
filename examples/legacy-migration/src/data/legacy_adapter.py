"""Legacy data adapter with architectural violation.

This file demonstrates a violation that should be tracked via baseline:
- Data layer importing from API layer (wrong direction)

This represents legacy code that was placed in the wrong layer
before architectural guidelines were established.
"""

# VIOLATION: Data layer should not depend on API layer
# This import creates a wrong-direction dependency
from src.api.user_controller import UserController


class LegacyDataAdapter:
    """Legacy adapter that violates layering rules.

    This was written before clean architecture was adopted.
    It should be refactored to remove the API dependency.

    To fix:
    1. Move any shared types to a common/models module
    2. Remove direct dependency on controller
    3. Use dependency injection instead
    """

    def __init__(self, controller: UserController) -> None:
        # Bad: Data layer should not know about controllers
        self._controller = controller

    def sync_from_api(self) -> None:
        """Legacy sync method - should be refactored."""
        # This violates the principle that data layer
        # should not depend on presentation layer
        pass
