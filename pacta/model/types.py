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
from typing import Any

# Core model entities


@dataclass(frozen=True, slots=True)
class Context:
    """
    Bounded Context (DDD).
    """

    id: str
    name: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class Layer:
    """
    Architectural layer definition inside a container.
    """

    id: str
    patterns: tuple[str, ...]  # glob patterns
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CodeMapping:
    """
    Defines how code paths map to architecture.
    """

    roots: tuple[str, ...]  # path roots for container ownership
    layers: Mapping[str, Layer]  # layer_id -> Layer


@dataclass(frozen=True, slots=True)
class Container:
    """
    Container / Service (C4 level 2).
    """

    id: str
    name: str | None = None
    context: str | None = None  # context id
    description: str | None = None

    code: CodeMapping | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Relation:
    """
    High-level container relationship.
    """

    from_container: str
    to_container: str
    protocol: str | None = None  # http, grpc, event, etc.
    description: str | None = None


# Architecture Model (root)


@dataclass(frozen=True, slots=True)
class ArchitectureModel:
    """
    High-level Architecture-as-Code model loaded from architecture.yaml.

    This model:
      - defines the architectural contract
      - is validated structurally
      - is used for IR enrichment (mapping)
      - is NEVER mutated during analysis
    """

    version: int

    contexts: Mapping[str, Context]
    containers: Mapping[str, Container]
    relations: tuple[Relation, ...]

    metadata: Mapping[str, Any] = field(default_factory=dict)

    # Convenience lookups (computed by ModelResolver)

    container_to_context: Mapping[str, str] = field(default_factory=dict)
    path_roots: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    layer_patterns: Mapping[str, Mapping[str, tuple[str, ...]]] = field(default_factory=dict)

    def get_container(self, container_id: str) -> Container | None:
        return self.containers.get(container_id)

    def get_context_for_container(self, container_id: str) -> str | None:
        return self.container_to_context.get(container_id)

    def get_layer_patterns(self, container_id: str) -> Mapping[str, tuple[str, ...]]:
        return self.layer_patterns.get(container_id, {})

    def all_container_ids(self) -> tuple[str, ...]:
        return tuple(self.containers.keys())

    def all_context_ids(self) -> tuple[str, ...]:
        return tuple(self.contexts.keys())
