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

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass

from pacta.reporting.types import Violation

# Stable hashing helpers


def _stable_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# Keys


@dataclass(frozen=True, slots=True)
class ViolationKeyStrategy:
    """
    Builds stable keys for violations so baselines can match the same violation
    across runs/commits.

    Default strategy (stable across runs):
    - Always includes rule id: v.rule.id
    - Uses context "subject identity":
      - dependency: (dep_type, src_id, dst_id)
      - node: (node_id)
    - If target is unknown, falls back to (rule_id + message)
    """

    def key_for(self, v: Violation) -> str:
        ctx = v.context or {}
        target = ctx.get("target")
        rule_id = v.rule.id

        if target == "dependency":
            payload = {
                "rule": rule_id,
                "target": "dependency",
                "dep_type": ctx.get("dep_type"),
                "src_id": ctx.get("src_id"),
                "dst_id": ctx.get("dst_id"),
            }
            return _sha1(_stable_json(payload))

        if target == "node":
            payload = {
                "rule": rule_id,
                "target": "node",
                "node_id": ctx.get("node_id"),
            }
            return _sha1(_stable_json(payload))

        payload = {
            "rule": rule_id,
            "target": target,
            "message": v.message,
        }
        return _sha1(_stable_json(payload))


# Baseline compare


@dataclass(frozen=True, slots=True)
class BaselineResult:
    """
    Compare output between current and baseline.

    - new: present now, not in baseline
    - existing: present now and in baseline
    - fixed: present in baseline, not present now
    """

    new: tuple[Violation, ...]
    existing: tuple[Violation, ...]
    fixed: tuple[Violation, ...]


@dataclass(frozen=True, slots=True)
class BaselineComparer:
    """
    Compare current violations against baseline violations.
    """

    key_strategy: ViolationKeyStrategy = ViolationKeyStrategy()

    def compare(self, current: Sequence[Violation], baseline: Sequence[Violation]) -> BaselineResult:
        cur_by_key: dict[str, Violation] = {self.key_strategy.key_for(v): v for v in current}
        base_by_key: dict[str, Violation] = {self.key_strategy.key_for(v): v for v in baseline}

        new_keys = cur_by_key.keys() - base_by_key.keys()
        existing_keys = cur_by_key.keys() & base_by_key.keys()
        fixed_keys = base_by_key.keys() - cur_by_key.keys()

        new = tuple(cur_by_key[k] for k in sorted(new_keys))
        existing = tuple(cur_by_key[k] for k in sorted(existing_keys))
        fixed = tuple(base_by_key[k] for k in sorted(fixed_keys))

        return BaselineResult(new=new, existing=existing, fixed=fixed)
