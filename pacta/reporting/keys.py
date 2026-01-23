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
from typing import Any


@dataclass(frozen=True, slots=True)
class DefaultViolationKeyFactory:
    """
    Factory for generating stable violation keys for baseline comparison.

    Violation keys are used to:
      - Track violations across snapshots
      - Determine if a violation is new/existing/fixed
      - Enable baseline comparison and drift detection

    Key strategy:
      - Combines rule ID + violation target information
      - Stable across runs (deterministic)
      - Unique enough to distinguish different violations
    """

    def create_key(self, violation: Any) -> str:
        """
        Create a stable key for a violation.

        Args:
            violation: Violation object (dict or dataclass)

        Returns:
            Stable string key for baseline comparison

        The key format depends on violation type:
          - For node violations: rule_id + node canonical ID
          - For dependency violations: rule_id + src + dst + dep_type
          - Fallback: rule_id + message hash
        """
        if isinstance(violation, dict):
            return self._key_from_dict(violation)

        # Assume dataclass/object
        return self._key_from_object(violation)

    def _key_from_dict(self, v: dict[str, Any]) -> str:
        rule_id = v.get("rule_id", v.get("rule", ""))

        # Check for node violation
        node = v.get("node")
        if node:
            node_id = self._extract_node_id(node)
            if node_id:
                return f"{rule_id}:node:{node_id}"

        # Check for dependency violation
        src = v.get("src")
        dst = v.get("dst")
        dep_type = v.get("dep_type", "")

        if src and dst:
            src_id = self._extract_node_id(src)
            dst_id = self._extract_node_id(dst)
            if src_id and dst_id:
                return f"{rule_id}:dep:{src_id}→{dst_id}:{dep_type}"

        # Fallback: rule + message
        message = v.get("message", "")
        return f"{rule_id}:{hash(message) & 0xFFFFFFFF:08x}"

    def _key_from_object(self, v: Any) -> str:
        rule_id = getattr(v, "rule_id", getattr(v, "rule", ""))

        # Check for node violation
        if hasattr(v, "node"):
            node_id = self._extract_node_id(v.node)
            if node_id:
                return f"{rule_id}:node:{node_id}"

        # Check for dependency violation
        if hasattr(v, "src") and hasattr(v, "dst"):
            src_id = self._extract_node_id(v.src)
            dst_id = self._extract_node_id(v.dst)
            dep_type = getattr(v, "dep_type", "")
            if src_id and dst_id:
                return f"{rule_id}:dep:{src_id}→{dst_id}:{dep_type}"

        # Fallback: rule + message
        message = getattr(v, "message", "")
        return f"{rule_id}:{hash(message) & 0xFFFFFFFF:08x}"

    def _extract_node_id(self, node: Any) -> str:
        """Extract canonical node ID from various formats."""
        if node is None:
            return ""

        # Dict format
        if isinstance(node, dict):
            # Try canonical_id first
            if "canonical_id" in node:
                return str(node["canonical_id"])
            if "id" in node:
                id_val = node["id"]
                if isinstance(id_val, dict):
                    # Structured ID: {language, code_root, fqname}
                    lang = id_val.get("language", "")
                    root = id_val.get("code_root", "")
                    fqname = id_val.get("fqname", "")
                    return f"{lang}://{root}::{fqname}"
                return str(id_val)
            # Fallback to fqname
            if "fqname" in node:
                return str(node["fqname"])
            return ""

        # Object format
        if hasattr(node, "id"):
            id_val = node.id
            # CanonicalId object
            if hasattr(id_val, "language") and hasattr(id_val, "fqname"):
                return f"{id_val.language}://{id_val.code_root}::{id_val.fqname}"
            return str(id_val)

        if hasattr(node, "canonical_id"):
            return str(node.canonical_id)

        if hasattr(node, "fqname"):
            return str(node.fqname)

        return str(node)

    def __call__(self, violation: Any) -> str:
        """Allow factory to be called directly as a function."""
        return self.create_key(violation)
