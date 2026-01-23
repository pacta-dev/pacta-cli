# SPDX-License-Identifier: AGPL-3.0-only
#
# Copyright (c) 2026 Pacta Contributors
#
# This file is part of Pacta.
#
# Pacta is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Pacta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.

from collections.abc import Mapping
from typing import Any


def get_field(obj: Any, *names: str, default: Any = None) -> Any:
    """
    Read a field from either:
    - Mapping (dict-like)
    - object attributes

    Tries names in order. Returns default if not found.
    """
    if obj is None:
        return default

    if isinstance(obj, Mapping):
        for n in names:
            if n in obj:
                return obj[n]
        return default

    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default
