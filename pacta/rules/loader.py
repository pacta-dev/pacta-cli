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

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pacta.rules.errors import RulesError


@dataclass(frozen=True, slots=True)
class RuleSource:
    """
    A single rules source file with its content.
    """

    path: Path
    content: str

    def __str__(self) -> str:
        return str(self.path)


@dataclass(frozen=True, slots=True)
class DefaultRuleSourceLoader:
    """
    Loads rule source files from filesystem.

    Responsibilities:
      - Read rule files from disk
      - Handle missing files gracefully with clear errors
      - Support multiple file formats (.rules, .yaml, .yml, .txt)
      - Return RuleSource objects for parser consumption
    """

    default_encoding: str = "utf-8"

    def load_sources(self, paths: Sequence[str | Path]) -> tuple[RuleSource, ...]:
        """
        Load multiple rules files and return their sources.

        Args:
            paths: Sequence of file paths to load

        Returns:
            Tuple of RuleSource objects

        Raises:
            RulesError: If any file cannot be read
        """
        sources: list[RuleSource] = []

        for path_input in paths:
            path = Path(path_input) if not isinstance(path_input, Path) else path_input

            if not path.exists():
                raise RulesError(
                    code="rule_file_not_found",
                    message=f"Rules file does not exist: {path}",
                    details={"path": str(path)},
                )

            if not path.is_file():
                raise RulesError(
                    code="rule_path_not_file",
                    message=f"Rules path is not a file: {path}",
                    details={"path": str(path)},
                )

            try:
                content = path.read_text(encoding=self.default_encoding)
            except UnicodeDecodeError as e:
                raise RulesError(
                    code="rule_file_encoding_error",
                    message=f"Failed to decode rules file (expected {self.default_encoding}): {path}",
                    details={"path": str(path), "error": str(e)},
                ) from e
            except Exception as e:
                raise RulesError(
                    code="rule_file_read_error",
                    message=f"Failed to read rules file: {path}",
                    details={"path": str(path), "error": str(e)},
                ) from e

            sources.append(RuleSource(path=path, content=content))

        return tuple(sources)

    def load_source(self, path: str | Path) -> RuleSource:
        """
        Load a single rules file.

        Convenience method for loading one file.
        """
        return self.load_sources([path])[0]
