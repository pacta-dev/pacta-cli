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

from dataclasses import dataclass, replace

from pacta.model.types import ArchitectureModel


@dataclass(frozen=True, slots=True)
class DefaultModelResolver:
    """
    Computes convenience lookup tables on the model.

    This keeps ArchitectureModel immutable: we return a new instance with populated fields:
      - container_to_context
      - path_roots
      - layer_patterns
    """

    def resolve(self, model: ArchitectureModel) -> ArchitectureModel:
        container_to_context: dict[str, str] = {}
        path_roots: dict[str, tuple[str, ...]] = {}
        layer_patterns: dict[str, dict[str, tuple[str, ...]]] = {}

        for cid, c in model.containers.items():
            if c.context:
                container_to_context[cid] = c.context

            if c.code is not None:
                roots = tuple(_norm_path(p) for p in c.code.roots if isinstance(p, str) and p.strip())
                # deterministic
                path_roots[cid] = tuple(sorted(set(roots)))

                layer_map: dict[str, tuple[str, ...]] = {}
                for layer_id, layer in c.code.layers.items():
                    pats = tuple(_norm_glob(p) for p in layer.patterns if isinstance(p, str) and p.strip())
                    layer_map[layer_id] = tuple(sorted(set(pats)))
                layer_patterns[cid] = dict(sorted(layer_map.items(), key=lambda kv: kv[0]))

        # deterministic ordering for dicts
        container_to_context = dict(sorted(container_to_context.items(), key=lambda kv: kv[0]))
        path_roots = dict(sorted(path_roots.items(), key=lambda kv: kv[0]))
        layer_patterns = dict(sorted(layer_patterns.items(), key=lambda kv: kv[0]))

        return replace(
            model,
            container_to_context=container_to_context,
            path_roots=path_roots,
            layer_patterns=layer_patterns,
        )


def _norm_path(p: str) -> str:
    # Keep it simple and stable across OS:
    # - use forward slashes
    # - strip leading "./"
    s = p.strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s.rstrip("/") if s != "/" else s


def _norm_glob(p: str) -> str:
    # For globs we keep them mostly intact but normalize slashes.
    return p.strip().replace("\\", "/")
