import fnmatch
import re
from collections.abc import Sequence


def match_glob(value: str | None, pattern: str) -> bool:
    """
    Glob match with Unix-style wildcards.
    - None never matches
    - case-sensitive by default (consistent across platforms)
    """
    if value is None:
        return False
    return fnmatch.fnmatchcase(value, pattern)


def match_any_glob(value: str | None, patterns: Sequence[str]) -> bool:
    if value is None:
        return False
    return any(fnmatch.fnmatchcase(value, p) for p in patterns)


def match_regex(value: str | None, regex: str) -> bool:
    """
    Regex match using Python re (search).
    - None never matches
    """
    if value is None:
        return False
    return re.search(regex, value) is not None
