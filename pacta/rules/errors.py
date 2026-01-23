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


class RulesError(Exception):
    """
    Base class for all rules-related errors.

    These errors should be surfaced to users as configuration/DSL issues,
    not as internal engine crashes.
    """

    code: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    details: Mapping[str, Any] | None = None

    def __init__(
        self,
        message: str,
        code: str = "rules_error",
        file: str | None = None,
        line: int | None = None,
        column: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.file = file
        self.line = line
        self.column = column
        self.details = details

    def __str__(self) -> str:
        loc = ""
        if self.file:
            loc = self.file
            if self.line is not None:
                loc += f":{self.line}"
                if self.column is not None:
                    loc += f":{self.column}"
            loc += ": "
        return f"{loc}{self.message}"


class RulesParseError(RulesError):
    """Raised when rules input cannot be parsed."""

    pass


class RulesCompileError(RulesError):
    """Raised when parsed rules cannot be compiled into runtime predicates."""

    pass


class RulesEvalError(RulesError):
    """Raised when evaluating compiled rules fails unexpectedly."""

    pass
