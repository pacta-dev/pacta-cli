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

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from pacta.snapshot.types import BaselineResult, ViolationStatus


def _get_field(obj: Any, names: Sequence[str]) -> Any:
    if isinstance(obj, Mapping):
        for n in names:
            if n in obj:
                return obj[n]
        return None
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None


def _set_status(obj: Any, status: ViolationStatus) -> Any:
    """
    Return a copy with status set if possible.
    Supports:
    - dataclass via replace()
    - dict mutation (copy)
    - object attribute set (fallback)
    """
    if isinstance(obj, Mapping):
        d = dict(obj)
        d["status"] = status
        return d

    # dataclass immutable pattern
    try:
        return replace(obj, status=status)
    except Exception:
        pass

    # mutable object
    try:
        obj.status = status
        return obj
    except Exception:
        return obj


class DefaultBaselineService:
    """
    Baseline comparison:
    - mark violations as new/existing/fixed/unknown
    - produce BaselineResult counters

    Expected baseline format:
    - a mapping { "violations": [ ... ] } OR
    - an iterable of violation objects/dicts
    """

    def mark_status(
        self,
        *,
        violations: Sequence[Any],
        baseline_snapshot: Any,
        key_factory: Any,
    ) -> list[Any]:
        """
        Mark violations with status relative to baseline snapshot.

        This is a convenience wrapper around mark_relative_to_baseline
        that matches the engine's expected interface.

        Args:
            violations: Current violations to mark
            baseline_snapshot: Baseline snapshot to compare against
            key_factory: Factory for generating violation keys (callable)

        Returns:
            List of violations with status field set
        """
        marked, _result = self.mark_relative_to_baseline(
            current_violations=violations,
            baseline=baseline_snapshot,
            key_fn=key_factory if callable(key_factory) else None,
        )
        return marked

    def mark_relative_to_baseline(
        self,
        current_violations: Sequence[Any],
        baseline: Any,
        *,
        key_fn: Callable[[Any], str] | None = None,
    ) -> tuple[list[Any], BaselineResult]:
        baseline_violations = self._extract_violations(baseline)

        cur_keys = [self._violation_key(v, key_fn=key_fn) for v in current_violations]
        base_keys = [self._violation_key(v, key_fn=key_fn) for v in baseline_violations]

        cur_key_set = {k for k in cur_keys if k}
        base_key_set = {k for k in base_keys if k}

        out: list[Any] = []
        new = existing = fixed = unknown = 0

        for v in current_violations:
            k = self._violation_key(v, key_fn=key_fn)
            if not k:
                out.append(_set_status(v, "unknown"))
                unknown += 1
                continue

            if k in base_key_set:
                out.append(_set_status(v, "existing"))
                existing += 1
            else:
                out.append(_set_status(v, "new"))
                new += 1

        # fixed = baseline violations that are not present now
        fixed = len(base_key_set - cur_key_set)

        return out, BaselineResult(new=new, existing=existing, fixed=fixed, unknown=unknown)

    def _extract_violations(self, baseline: Any) -> Sequence[Any]:
        if baseline is None:
            return []
        if isinstance(baseline, Mapping):
            v = baseline.get("violations")
            if isinstance(v, list):
                return v
            return []
        if isinstance(baseline, (list, tuple)):
            return baseline
        if hasattr(baseline, "violations"):
            v = baseline.violations
            if isinstance(v, (list, tuple)):
                return list(v)
        return []

    def _violation_key(self, v: Any, *, key_fn: Callable[[Any], str] | None) -> str:
        if key_fn is not None:
            try:
                return str(key_fn(v))
            except Exception:
                return ""

        k = _get_field(v, ["violation_key", "key", "signature", "id"])
        if k is None:
            return ""
        return str(k)
