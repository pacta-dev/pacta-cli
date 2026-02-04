from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import auto
from typing import Any

from pacta.utils.enum import StrEnum

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
    name: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CodeMapping:
    """
    Defines how code paths map to architecture.
    """

    roots: tuple[str, ...]  # path roots for container ownership
    layers: Mapping[str, Layer]  # layer_id -> Layer


class ContainerKind(StrEnum):
    SERVICE = auto()
    MODULE = auto()
    LIBRARY = auto()


@dataclass(frozen=True, slots=True)
class Container:
    """
    Container / Service (C4 level 2).

    In v2 schemas, containers can nest via ``children`` and carry an explicit
    ``kind`` (service, module, library).  Nested containers are flattened
    into dot-qualified IDs (e.g. ``billing-service.invoice-module``).
    """

    id: str
    name: str | None = None
    context: str | None = None  # context id
    description: str | None = None

    code: CodeMapping | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    # v2 fields
    kind: ContainerKind | None = None
    children: Mapping[str, "Container"] = field(default_factory=dict)  # populated from "contains" YAML key
    parent: str | None = None  # dot-qualified ID of parent container, set by resolver


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

    @property
    def containers_flat(self) -> Mapping[str, Container]:
        """All containers including nested ones, keyed by dot-qualified ID."""
        result: dict[str, Container] = {}
        _collect_containers(self.containers, "", result)
        return result

    def get_container(self, container_id: str) -> Container | None:
        return self.containers_flat.get(container_id)

    def get_context_for_container(self, container_id: str) -> str | None:
        return self.container_to_context.get(container_id)

    def get_layer_patterns(self, container_id: str) -> Mapping[str, tuple[str, ...]]:
        return self.layer_patterns.get(container_id, {})

    def all_container_ids(self) -> tuple[str, ...]:
        return tuple(self.containers_flat.keys())

    def all_context_ids(self) -> tuple[str, ...]:
        return tuple(self.contexts.keys())


def _collect_containers(
    containers: Mapping[str, Container],
    prefix: str,
    out: dict[str, Container],
) -> None:
    """Recursively collect containers into a flat dict with dot-qualified keys."""
    for cid, container in containers.items():
        qualified = f"{prefix}.{cid}" if prefix else cid
        out[qualified] = container
        if container.children:
            _collect_containers(container.children, qualified, out)
