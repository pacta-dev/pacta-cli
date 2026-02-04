"""Tests for IR serialization backward compatibility (v1 snapshots with v2 code)."""

from pacta.ir.types import (
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SymbolKind,
)


def cid(fqname: str) -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root="repo", fqname=fqname)


def test_node_from_dict_without_v2_fields():
    """v1 snapshot data (no service, container_kind) deserializes with None defaults."""
    data = {
        "id": {"language": "python", "code_root": "repo", "fqname": "a.b"},
        "kind": "module",
        "name": "b",
        "path": "a/b.py",
        "loc": None,
        "container": "svc",
        "layer": "domain",
        "context": "billing",
        "tags": ["internal"],
        "attributes": {},
    }
    node = IRNode.from_dict(data)
    assert node.container == "svc"
    assert node.service is None
    assert node.container_kind is None


def test_node_roundtrip_with_v2_fields():
    """v2 node serializes and deserializes with new fields."""
    node = IRNode(
        id=cid("a.b"),
        kind=SymbolKind.MODULE,
        name="b",
        path="a/b.py",
        container="billing-service.invoice-module",
        layer="domain",
        context="billing",
        service="billing-service",
        container_kind="module",
    )
    data = node.to_dict()
    assert data["service"] == "billing-service"
    assert data["container_kind"] == "module"

    restored = IRNode.from_dict(data)
    assert restored.service == "billing-service"
    assert restored.container_kind == "module"


def test_edge_from_dict_without_v2_fields():
    """v1 snapshot edge data deserializes with None for new fields."""
    data = {
        "src": {"language": "python", "code_root": "repo", "fqname": "a"},
        "dst": {"language": "python", "code_root": "repo", "fqname": "b"},
        "dep_type": "import",
        "loc": None,
        "confidence": 1.0,
        "details": {},
        "src_container": "svc",
        "src_layer": "domain",
        "src_context": "billing",
        "dst_container": "svc",
        "dst_layer": "infra",
        "dst_context": "billing",
    }
    edge = IREdge.from_dict(data)
    assert edge.src_container == "svc"
    assert edge.src_service is None
    assert edge.dst_service is None
    assert edge.src_container_kind is None
    assert edge.dst_container_kind is None


def test_edge_roundtrip_with_v2_fields():
    """v2 edge serializes and deserializes with new fields."""
    edge = IREdge(
        src=cid("a"),
        dst=cid("b"),
        dep_type=DepType.IMPORT,
        src_service="billing-service",
        dst_service="shared-utils",
        src_container_kind="service",
        dst_container_kind="library",
    )
    data = edge.to_dict()
    assert data["src_service"] == "billing-service"
    assert data["dst_container_kind"] == "library"

    restored = IREdge.from_dict(data)
    assert restored.src_service == "billing-service"
    assert restored.dst_service == "shared-utils"
    assert restored.src_container_kind == "service"
    assert restored.dst_container_kind == "library"
