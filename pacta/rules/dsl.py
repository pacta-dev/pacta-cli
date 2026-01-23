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

from pacta.rules.ast import RuleAst, RulesDocumentAst
from pacta.rules.loader import RuleSource
from pacta.rules.parser import DslRulesParserV0


@dataclass(frozen=True, slots=True)
class DefaultDSLParser:
    """
    High-level DSL parser that processes multiple rule sources.

    This is a facade over DslRulesParserV0 that:
      - Parses multiple RuleSource objects
      - Merges them into a single RulesDocumentAst
      - Provides a clean interface for the engine

    The parser delegates to DslRulesParserV0 for actual parsing logic.
    """

    def parse_many(
        self,
        sources: Sequence[RuleSource],
        *,
        source_names: Sequence[str] | None = None,
    ) -> RulesDocumentAst:
        """
        Parse multiple rule sources and merge into a single document.

        Args:
            sources: Sequence of RuleSource objects to parse
            source_names: Optional human-readable names for error messages
                         (defaults to using source.path)

        Returns:
            Single RulesDocumentAst containing all rules from all sources

        Raises:
            RulesParseError: If parsing fails
        """
        if not sources:
            # Empty sources = empty document
            return RulesDocumentAst(rules=(), span=None)

        parser = DslRulesParserV0()
        all_rules: list[RuleAst] = []

        for i, source in enumerate(sources):
            # Use provided name or fall back to source path
            if source_names and i < len(source_names):
                filename = source_names[i]
            else:
                filename = str(source.path)

            # Parse this source
            doc = parser.parse_text(source.content, filename=filename)

            # Accumulate rules
            all_rules.extend(doc.rules)

        # Return merged document
        # Note: We don't preserve individual spans since we merged multiple files
        return RulesDocumentAst(rules=tuple(all_rules), span=None)

    def parse_one(self, source: RuleSource) -> RulesDocumentAst:
        """
        Parse a single rule source.

        Convenience method for parsing one source.
        """
        return self.parse_many([source])
