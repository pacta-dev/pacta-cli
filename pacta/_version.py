from importlib.metadata import version
from importlib.metadata import PackageNotFoundError


def _detect_version() -> str:
    """
    Detect pacta version.

    Falls back to a development placeholder if the package metadata
    is not available.
    """
    try:
        return version("pacta")
    except PackageNotFoundError:
        return "0.0.0-dev"
