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

from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path
from typing import Final

from pacta.ir.types import Language
from pacta.plugins.interfaces import Analyzer

ENTRYPOINT_GROUP: Final[str] = "pacta.analyzers"


@dataclass(frozen=True, slots=True)
class LoadedAnalyzer:
    """
    Analyzer instance together with its provenance (useful for debugging).
    """

    analyzer: Analyzer
    source: str  # e.g. "pacta_python.plugin:PythonAnalyzer"


@dataclass(frozen=True, slots=True)
class PluginLoadError:
    """
    Represents a failure to load a plugin (kept non-fatal).
    """

    source: str
    error: str


class AnalyzerRegistry:
    """
    Discovers and stores analyzer plugins.

    Typical lifecycle:
      reg = AnalyzerRegistry()
      reg.load_entrypoints()
      analyzers = reg.best_for_repo(repo_root)
    """

    def __init__(self) -> None:
        self._loaded: list[LoadedAnalyzer] = []
        self._load_errors: list[PluginLoadError] = []
        self._entrypoints_loaded: bool = False

    def load_entrypoints(self) -> None:
        """
        Discover analyzers registered under entrypoint group 'pacta.analyzers'.

        Rules:
        - Must be safe: plugin import errors must not crash the whole tool.
        - Accept both:
            1) a class (callable) returning Analyzer instance
            2) a singleton Analyzer instance
        - If called multiple times, does nothing after first successful call.
        """
        if self._entrypoints_loaded:
            return

        eps = entry_points()
        # Python 3.10+ supports select(); older returns dict-like
        group = eps.select(group=ENTRYPOINT_GROUP) if hasattr(eps, "select") else eps.get(ENTRYPOINT_GROUP, [])

        for ep in group:
            source = f"{ep.module}:{ep.attr}"
            try:
                loaded_obj = ep.load()

                # Allow either:
                #  - analyzer instance (implements Analyzer protocol)
                #  - analyzer factory/class (callable)
                analyzer = loaded_obj() if callable(loaded_obj) else loaded_obj

                # Best-effort sanity checks
                _ = analyzer.plugin_id  # may throw if missing
                _ = analyzer.language

                self._loaded.append(LoadedAnalyzer(analyzer=analyzer, source=source))
            except Exception as e:
                self._load_errors.append(PluginLoadError(source=source, error=repr(e)))

        self._entrypoints_loaded = True

    def register(self, analyzer: Analyzer, *, source: str = "manual") -> None:
        """
        Manual registration (useful for unit tests or embedding).
        """
        self._loaded.append(LoadedAnalyzer(analyzer=analyzer, source=source))

    def all(self) -> tuple[LoadedAnalyzer, ...]:
        """
        Returns all successfully loaded analyzers.
        """
        return tuple(self._loaded)

    def load_errors(self) -> tuple[PluginLoadError, ...]:
        """
        Returns non-fatal plugin load errors.
        """
        return tuple(self._load_errors)

    def by_language(self, language: Language) -> tuple[LoadedAnalyzer, ...]:
        """
        Returns analyzers for a specific language.
        """
        return tuple(a for a in self._loaded if a.analyzer.language == language)

    def best_for_repo(self, repo_root: Path) -> tuple[LoadedAnalyzer, ...]:
        """
        Select analyzers that claim they can analyze the repository.
        Multiple analyzers can be returned (polyglot repo).

        Note:
        - can_analyze() must be quick and should not parse deeply.
        - Failures in can_analyze() are treated as "cannot analyze".
        """
        repo_root = repo_root.resolve()
        selected: list[LoadedAnalyzer] = []

        for loaded in self._loaded:
            try:
                if loaded.analyzer.can_analyze(repo_root):
                    selected.append(loaded)
            except Exception:
                # If plugin check fails, ignore it (non-fatal)
                continue

        # Deterministic ordering: sort by plugin_id then source
        selected.sort(key=lambda a: (getattr(a.analyzer, "plugin_id", ""), a.source))
        return tuple(selected)
