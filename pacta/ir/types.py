from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import auto
from pathlib import Path
from typing import Any

from pacta.utils.enum import StrEnum

# Enums


class Language(StrEnum):
    PYTHON = auto()
    JAVA = auto()
    TYPESCRIPT = auto()
    JAVASCRIPT = auto()
    GO = auto()
    UNKNOWN = auto()


class SymbolKind(StrEnum):
    REPO = auto()
    CONTAINER = auto()
    FILE = auto()
    PACKAGE = auto()
    MODULE = auto()
    CLASS = auto()
    INTERFACE = auto()
    FUNCTION = auto()
    METHOD = auto()
    VARIABLE = auto()


class DepType(StrEnum):
    IMPORT = auto()
    REQUIRE = auto()
    INCLUDE = auto()
    TYPE_REF = auto()
    CALL = auto()

    # Higher-level (optional extractors)
    HTTP_CALL = auto()
    EVENT_PUBLISH = auto()
    EVENT_CONSUME = auto()
    DB_QUERY = auto()


# Source location


@dataclass(frozen=True, slots=True)
class SourcePos:
    line: int
    column: int = 1

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "SourcePos":
        return SourcePos(
            line=data["line"],
            column=data["column"] if data.get("column") else 1,
        )


@dataclass(frozen=True, slots=True)
class SourceLoc:
    file: str
    start: SourcePos
    end: SourcePos | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "start": {"line": self.start.line, "column": self.start.column},
            "end": None if self.end is None else {"line": self.end.line, "column": self.end.column},
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "SourceLoc":
        return SourceLoc(
            file=data["file"],
            start=SourcePos.from_dict(data["start"]),
            end=SourcePos.from_dict(data["end"]) if data.get("end") is not None else None,
        )


# Canonical identifier


@dataclass(frozen=True, slots=True)
class CanonicalId:
    """
    Stable, cross-language identifier.

    Format:
      {language}://{code_root}::{fqname}

    Example:
      python://billing-service::services.billing.domain.invoice
    """

    language: Language
    code_root: str
    fqname: str

    def __str__(self) -> str:
        return f"{self.language.value}://{self.code_root}::{self.fqname}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language.value,
            "code_root": self.code_root,
            "fqname": self.fqname,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "CanonicalId":
        return CanonicalId(
            language=Language(data["language"]),
            code_root=data["code_root"],
            fqname=data["fqname"],
        )


# IR Node


@dataclass(frozen=True, slots=True)
class IRNode:
    """
    A node represents a code artifact (file/module/class/etc).
    """

    id: CanonicalId
    kind: SymbolKind

    # Best-effort metadata
    name: str | None = None
    path: str | None = None
    loc: SourceLoc | None = None

    # Enriched by mapping layer
    container: str | None = None
    layer: str | None = None
    context: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

    # v2: service-level enrichment
    service: str | None = None  # top-level container ancestor
    container_kind: str | None = None  # immediate container kind (service/module/library)
    within: str | None = None  # top-level container's kind (for nested containers)

    attributes: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id.to_dict(),
            "kind": self.kind.value,
            "name": self.name,
            "path": self.path,
            "loc": None if self.loc is None else self.loc.to_dict(),
            "container": self.container,
            "layer": self.layer,
            "context": self.context,
            "tags": list(self.tags),
            "service": self.service,
            "container_kind": self.container_kind,
            "within": self.within,
            "attributes": dict(self.attributes),
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "IRNode":
        return IRNode(
            id=CanonicalId.from_dict(data["id"]),
            kind=SymbolKind(data["kind"]),
            name=data.get("name"),
            path=data.get("path"),
            loc=None if data.get("loc") is None else SourceLoc.from_dict(data["loc"]),
            container=data.get("container"),
            layer=data.get("layer"),
            context=data.get("context"),
            tags=tuple(data.get("tags", [])),
            service=data.get("service"),
            container_kind=data.get("container_kind"),
            within=data.get("within"),
            attributes=dict(data.get("attributes", {})),
        )


# IR Edge


@dataclass(frozen=True, slots=True)
class IREdge:
    """
    Directed dependency edge between two IR nodes.
    """

    src: CanonicalId
    dst: CanonicalId
    dep_type: DepType

    loc: SourceLoc | None = None
    confidence: float = 1.0
    details: Mapping[str, Any] = field(default_factory=dict)

    # Enriched by mapping layer
    src_container: str | None = None
    src_layer: str | None = None
    src_context: str | None = None
    dst_container: str | None = None
    dst_layer: str | None = None
    dst_context: str | None = None

    # v2: service-level enrichment
    src_service: str | None = None
    dst_service: str | None = None
    src_container_kind: str | None = None
    dst_container_kind: str | None = None
    src_within: str | None = None  # top-level container's kind for source
    dst_within: str | None = None  # top-level container's kind for destination

    def to_dict(self) -> dict[str, Any]:
        return {
            "src": self.src.to_dict(),
            "dst": self.dst.to_dict(),
            "dep_type": self.dep_type.value,
            "loc": None if self.loc is None else self.loc.to_dict(),
            "confidence": self.confidence,
            "details": dict(self.details),
            "src_container": self.src_container,
            "src_layer": self.src_layer,
            "src_context": self.src_context,
            "dst_container": self.dst_container,
            "dst_layer": self.dst_layer,
            "dst_context": self.dst_context,
            "src_service": self.src_service,
            "dst_service": self.dst_service,
            "src_container_kind": self.src_container_kind,
            "dst_container_kind": self.dst_container_kind,
            "src_within": self.src_within,
            "dst_within": self.dst_within,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "IREdge":
        return IREdge(
            src=CanonicalId.from_dict(data["src"]),
            dst=CanonicalId.from_dict(data["dst"]),
            dep_type=DepType(data["dep_type"]),
            loc=None if data.get("loc") is None else SourceLoc.from_dict(data["loc"]),
            confidence=float(data.get("confidence", 1.0)),
            details=dict(data.get("details", {})),
            src_container=data.get("src_container"),
            src_layer=data.get("src_layer"),
            src_context=data.get("src_context"),
            dst_container=data.get("dst_container"),
            dst_layer=data.get("dst_layer"),
            dst_context=data.get("dst_context"),
            src_service=data.get("src_service"),
            dst_service=data.get("dst_service"),
            src_container_kind=data.get("src_container_kind"),
            dst_container_kind=data.get("dst_container_kind"),
            src_within=data.get("src_within"),
            dst_within=data.get("dst_within"),
        )


# Architecture IR (the main object)


@dataclass(frozen=True, slots=True)
class ArchitectureIR:
    """
    Language-agnostic Intermediate Representation of architecture facts.

    This is the ONLY structure that:
      - analyzers produce
      - rules evaluate
      - snapshots store
      - diffs compare
    """

    schema_version: int
    produced_by: str  # e.g. "pacta-python@0.1.0"
    repo_root: str

    nodes: tuple[IRNode, ...]
    edges: tuple[IREdge, ...]

    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls, repo_root: str | Path) -> "ArchitectureIR":
        """
        Convenience constructor for an empty IR.
        """
        return cls(
            schema_version=2,
            produced_by="pacta-core",
            repo_root=str(repo_root),
            nodes=(),
            edges=(),
            metadata={},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "produced_by": self.produced_by,
            "repo_root": self.repo_root,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": dict(self.metadata),
        }
