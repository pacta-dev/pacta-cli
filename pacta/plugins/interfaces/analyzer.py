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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from pacta.ir.types import ArchitectureIR, Language


@dataclass(frozen=True, slots=True)
class AnalyzeTarget:
    """
    Restricts analysis scope.

    If you run in "changed-only" mode, the core can pass a limited set of paths
    here so analyzers don't scan the whole repository.
    """

    include_paths: tuple[Path, ...] = field(default_factory=tuple)
    exclude_globs: tuple[str, ...] = field(default_factory=tuple)

    def is_empty(self) -> bool:
        return not self.include_paths and not self.exclude_globs


# AnalyzeConfig (main)


@dataclass(frozen=True, slots=True)
class AnalyzeConfig:
    """
    Shared configuration passed from the core engine to analyzers.

    IMPORTANT:
    - This is a *stable contract* between core and plugins.
    - Add fields carefully; keep defaults backward-compatible.
    - Analyzers should not mutate it.
    """

    repo_root: Path

    # Optional: restrict scanning (changed-only / partial analysis)
    target: AnalyzeTarget = field(default_factory=AnalyzeTarget)

    # Determinism and safety
    deterministic: bool = True
    max_file_size_bytes: int = 2_000_000

    # Arbitrary analyzer options (per-language/per-plugin).
    # Examples:
    #   language_options["typescript"] = {"tsconfig": "tsconfig.json"}
    #   language_options["java"] = {"source": "17", "classpath": "..."}
    language_options: Mapping[str, Any] = field(default_factory=dict)

    # Repository metadata (optional), useful for reporting and caching.
    # Examples: commit hash, branch name, CI run id
    repo_metadata: Mapping[str, Any] = field(default_factory=dict)

    # Caching hints (optional):
    # analyzers may store their own caches under this directory if set.
    cache_dir: Path | None = None

    def normalized_repo_root(self) -> Path:
        """
        Returns a resolved repo root path for consistent behavior.
        """
        return self.repo_root.resolve()


# Analyzer protocol (context for AnalyzeConfig)


class Analyzer(Protocol):
    """
    Analyzer plugin contract.

    An analyzer extracts language-specific facts from code
    and outputs a language-agnostic ArchitectureIR.
    """

    @property
    def language(self) -> Language:
        """
        Primary language this analyzer supports (python/java/typescript/go/...).
        """
        raise NotImplementedError()

    @property
    def plugin_id(self) -> str:
        """
        Stable plugin id used in produced_by / reporting.
        Example: "pacta-python", "pacta-java".
        """
        raise NotImplementedError()

    def can_analyze(self, repo_root: Path) -> bool:
        """
        Lightweight detection check:
        e.g., contains *.py / pom.xml / package.json / go.mod etc.
        Must be fast and not do deep parsing.
        """
        raise NotImplementedError()

    def analyze(self, config: AnalyzeConfig) -> ArchitectureIR:
        """
        Run analysis and return ArchitectureIR.

        Determinism requirement:
        - If config.deterministic is True, output must be stable across runs.
        - Nodes/edges ordering should be deterministic (or left to normalizer).
        """
        raise NotImplementedError()
