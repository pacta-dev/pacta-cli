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

# CI-friendly semantics
EXIT_OK = 0
EXIT_NEW_VIOLATIONS = 1
EXIT_ENGINE_ERROR = 2


def _safe_get(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = mapping
    for k in keys:
        if not isinstance(cur, Mapping) or k not in cur:
            return default
        cur = cur[k]
    return cur


def exit_code_from_report_dict(report: Mapping[str, Any]) -> int:
    """
    Determine exit code from a dict-shaped report (Report.to_dict()).
    Policy:
      - engine_errors > 0 => EXIT_ENGINE_ERROR
      - any ERROR violations with status NEW (or missing status) => EXIT_NEW_VIOLATIONS
      - else EXIT_OK
    """
    engine_errors = _safe_get(report, "summary", "engine_errors", default=0)
    if isinstance(engine_errors, int) and engine_errors > 0:
        return EXIT_ENGINE_ERROR

    violations = report.get("violations", [])
    for v in violations if isinstance(violations, list) else []:
        try:
            rule = v.get("rule", {}) if isinstance(v, dict) else {}
            severity = rule.get("severity", "error")
            status = v.get("status", "unknown")
            if severity == "error" and status in ("new", "unknown"):
                return EXIT_NEW_VIOLATIONS
        except Exception:
            continue

    return EXIT_OK
