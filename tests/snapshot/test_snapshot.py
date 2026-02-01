from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


@dataclass(frozen=True, slots=True)
class FakeCanonicalId:
    value: str

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value}

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "FakeCanonicalId":
        return FakeCanonicalId(value=str(data["value"]))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class FakeLoc:
    file: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "line": self.line}

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "FakeLoc":
        return FakeLoc(file=str(data["file"]), line=int(data["line"]))


@dataclass(frozen=True, slots=True)
class FakeIRNode:
    id: FakeCanonicalId
    kind: str
    name: str | None = None
    path: str | None = None
    loc: FakeLoc | None = None
    container: str | None = None
    layer: str | None = None
    context: str | None = None
    tags: tuple[str, ...] = ()
    attributes: Mapping[str, Any] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id.to_dict(),
            "kind": self.kind,
            "name": self.name,
            "path": self.path,
            "loc": None if self.loc is None else self.loc.to_dict(),
            "container": self.container,
            "layer": self.layer,
            "context": self.context,
            "tags": list(self.tags),
            "attributes": dict(self.attributes) if isinstance(self.attributes, Mapping) else {},
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "FakeIRNode":
        return FakeIRNode(
            id=FakeCanonicalId.from_dict(data["id"]),
            kind=str(data["kind"]),
            name=data.get("name"),
            path=data.get("path"),
            loc=None if data.get("loc") is None else FakeLoc.from_dict(data["loc"]),
            container=data.get("container"),
            layer=data.get("layer"),
            context=data.get("context"),
            tags=tuple(data.get("tags", [])),
            attributes=dict(data.get("attributes", {})),
        )


@dataclass(frozen=True, slots=True)
class FakeIREdge:
    src: FakeCanonicalId
    dst: FakeCanonicalId
    dep_type: str
    loc: FakeLoc | None = None
    confidence: float = 1.0
    details: Mapping[str, Any] = ()
    src_container: str | None = None
    src_layer: str | None = None
    src_context: str | None = None
    dst_container: str | None = None
    dst_layer: str | None = None
    dst_context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "src": self.src.to_dict(),
            "dst": self.dst.to_dict(),
            "dep_type": self.dep_type,
            "loc": None if self.loc is None else self.loc.to_dict(),
            "confidence": self.confidence,
            "details": dict(self.details) if isinstance(self.details, Mapping) else {},
            "src_container": self.src_container,
            "src_layer": self.src_layer,
            "src_context": self.src_context,
            "dst_container": self.dst_container,
            "dst_layer": self.dst_layer,
            "dst_context": self.dst_context,
        }

    @staticmethod
    def from_dict(data: Mapping[str, Any]) -> "FakeIREdge":
        return FakeIREdge(
            src=FakeCanonicalId.from_dict(data["src"]),
            dst=FakeCanonicalId.from_dict(data["dst"]),
            dep_type=str(data["dep_type"]),
            loc=None if data.get("loc") is None else FakeLoc.from_dict(data["loc"]),
            confidence=float(data.get("confidence", 1.0)),
            details=dict(data.get("details", {})),
            src_container=data.get("src_container"),
            src_layer=data.get("src_layer"),
            src_context=data.get("src_context"),
            dst_container=data.get("dst_container"),
            dst_layer=data.get("dst_layer"),
            dst_context=data.get("dst_context"),
        )


def make_node(key: str, *, extra: dict[str, Any] | None = None) -> FakeIRNode:
    return FakeIRNode(
        id=FakeCanonicalId(key),
        kind="module",
        name=f"n-{key}",
        path=f"pkg/{key}.py",
        attributes=(extra or {}),
    )


def make_edge(src: str, dst: str, *, details: dict[str, Any] | None = None) -> FakeIREdge:
    return FakeIREdge(
        src=FakeCanonicalId(src),
        dst=FakeCanonicalId(dst),
        dep_type="import",
        confidence=1.0,
        details=(details or {}),
    )


class IRShapeAttrs:
    def __init__(self, nodes: Sequence[Any], edges: Sequence[Any]) -> None:
        self.nodes = nodes
        self.edges = edges


class IRShapeGetters:
    def __init__(self, nodes: Sequence[Any], edges: Sequence[Any]) -> None:
        self._nodes = nodes
        self._edges = edges

    def get_nodes(self) -> Sequence[Any]:
        return self._nodes

    def get_edges(self) -> Sequence[Any]:
        return self._edges


@pytest.fixture(autouse=True)
def patch_snapshot_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure snapshot loads don't depend on real pacta.ir.types.
    This patch assumes Snapshot.from_dict uses module globals IRNode/IREdge.
    """
    import pacta.snapshot.types as snap_types

    monkeypatch.setattr(snap_types, "IRNode", FakeIRNode, raising=False)
    monkeypatch.setattr(snap_types, "IREdge", FakeIREdge, raising=False)


@pytest.fixture
def meta(tmp_path: Path):
    from pacta.snapshot.types import SnapshotMeta

    return SnapshotMeta(repo_root=str(tmp_path), commit="abc123", branch="main", tool_version="0.0-test")


def test_builder_accepts_attr_ir_and_sorts_deterministically(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder

    # intentionally unsorted
    n2 = make_node("b")
    n1 = make_node("a")
    e2 = make_edge("b", "a")
    e1 = make_edge("a", "b")

    ir = IRShapeAttrs(nodes=[n2, n1], edges=[e2, e1])

    snap = DefaultSnapshotBuilder(schema_version=1).build(ir, meta=meta)

    assert snap.schema_version == 1
    assert snap.meta.repo_root == meta.repo_root
    assert snap.meta.commit == "abc123"
    assert snap.meta.branch == "main"
    assert snap.meta.tool_version == "0.0-test"

    # deterministic order
    assert [str(n.id) for n in snap.nodes] == ["a", "b"]
    # edge key sorts by stable representation; both present
    assert len(snap.edges) == 2
    assert snap.meta.created_at is not None


def test_builder_accepts_getter_ir(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder

    ir = IRShapeGetters(nodes=[make_node("x")], edges=[make_edge("x", "y")])
    snap = DefaultSnapshotBuilder().build(ir, meta=meta)

    assert len(snap.nodes) == 1
    assert len(snap.edges) == 1


def test_builder_accepts_dict_ir(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder

    ir = {"nodes": [make_node("k")], "edges": [make_edge("k", "m")]}
    snap = DefaultSnapshotBuilder().build(ir, meta=meta)
    assert len(snap.nodes) == 1
    assert len(snap.edges) == 1


def test_builder_raises_on_invalid_ir(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder

    with pytest.raises(TypeError):
        DefaultSnapshotBuilder().build(object(), meta=meta)


def test_builder_preserves_given_created_at(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.types import SnapshotMeta

    meta2 = SnapshotMeta(
        repo_root=meta.repo_root,
        commit=meta.commit,
        branch=meta.branch,
        created_at="2026-01-01T00:00:00Z",
        tool_version=meta.tool_version,
    )
    snap = DefaultSnapshotBuilder().build({"nodes": [], "edges": []}, meta=meta2)
    assert snap.meta.created_at == "2026-01-01T00:00:00Z"


def test_store_refs_and_objects(tmp_path: Path):
    """Test the new content-addressed storage with refs."""
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.store import FsSnapshotStore
    from pacta.snapshot.types import SnapshotMeta

    store = FsSnapshotStore(repo_root=str(tmp_path))
    meta = SnapshotMeta(repo_root=str(tmp_path))
    ir = {"nodes": [], "edges": []}
    snap = DefaultSnapshotBuilder().build(ir, meta=meta)

    # Save with refs
    result = store.save(snap, refs=["latest", "baseline"])

    # Check object was created
    assert result.object_path.exists()
    assert result.short_hash in result.object_path.name

    # Check refs were created
    assert store.ref_exists("latest")
    assert store.ref_exists("baseline")
    assert store.resolve_ref("latest") == result.short_hash
    assert store.resolve_ref("baseline") == result.short_hash

    # Load by ref
    loaded = store.load("latest")
    assert loaded.schema_version == snap.schema_version

    # Load by hash
    loaded2 = store.load(result.short_hash)
    assert loaded2.schema_version == snap.schema_version


def test_store_save_creates_dirs_and_is_deterministic(tmp_path: Path, meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.store import FsSnapshotStore

    store = FsSnapshotStore(repo_root=str(tmp_path))

    ir = {"nodes": [make_node("b"), make_node("a")], "edges": [make_edge("a", "b")]}
    snap = DefaultSnapshotBuilder().build(ir, meta=meta)

    result1 = store.save(snap, refs=["latest"])
    assert result1.object_path.exists()

    text1 = result1.object_path.read_text(encoding="utf-8")

    # Save again: should produce same hash (content-addressed)
    result2 = store.save(snap, refs=["latest"])
    text2 = result2.object_path.read_text(encoding="utf-8")
    assert text1 == text2
    assert result1.short_hash == result2.short_hash  # Same content = same hash


def test_store_roundtrip_save_load(tmp_path: Path, meta, monkeypatch: pytest.MonkeyPatch):
    """
    Requires Snapshot.from_dict to exist.
    If you haven't added it yet, this test will xfail with a clear message.
    """
    import pacta.snapshot.types as snap_types
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.store import FsSnapshotStore

    if not hasattr(snap_types.Snapshot, "from_dict"):
        pytest.xfail("Snapshot.from_dict is not implemented yet; add it to pacta/snapshot/types.py.")

    store = FsSnapshotStore(repo_root=str(tmp_path))

    ir = {"nodes": [make_node("a")], "edges": [make_edge("a", "b")]}
    snap = DefaultSnapshotBuilder().build(ir, meta=meta)

    store.save(snap, refs=["latest"])
    loaded = store.load("latest")

    assert loaded.schema_version == snap.schema_version
    assert loaded.meta.repo_root == snap.meta.repo_root
    assert [n.to_dict() for n in loaded.nodes] == [n.to_dict() for n in snap.nodes]
    assert [e.to_dict() for e in loaded.edges] == [e.to_dict() for e in snap.edges]


def test_diff_empty_is_empty(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.diff import DefaultSnapshotDiffEngine

    ir = {"nodes": [make_node("a")], "edges": [make_edge("a", "b")]}
    snap1 = DefaultSnapshotBuilder().build(ir, meta=meta)
    snap2 = DefaultSnapshotBuilder().build(ir, meta=meta)

    d = DefaultSnapshotDiffEngine().diff(snap1, snap2, include_details=True)
    assert d.is_empty()
    assert d.nodes_added == 0
    assert d.nodes_removed == 0
    assert d.edges_added == 0
    assert d.edges_removed == 0
    assert d.details["nodes"]["added"] == []
    assert d.details["edges"]["removed"] == []


def test_diff_added_removed(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.diff import DefaultSnapshotDiffEngine

    before = DefaultSnapshotBuilder().build(
        {"nodes": [make_node("a")], "edges": [make_edge("a", "b")]},
        meta=meta,
    )
    after = DefaultSnapshotBuilder().build(
        {"nodes": [make_node("a"), make_node("c")], "edges": [make_edge("a", "b"), make_edge("c", "a")]},
        meta=meta,
    )

    d = DefaultSnapshotDiffEngine().diff(before, after, include_details=True)
    assert d.nodes_added == 1
    assert d.nodes_removed == 0
    assert d.edges_added == 1
    assert d.edges_removed == 0
    assert "c" in "".join(d.details["nodes"]["added"])  # key contains c somehow


def test_diff_changed_detection_same_key_different_content(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.diff import DefaultSnapshotDiffEngine

    # Same node id "a" but different attributes -> should be "changed"
    before = DefaultSnapshotBuilder().build(
        {"nodes": [make_node("a", extra={"x": 1})], "edges": []},
        meta=meta,
    )
    after = DefaultSnapshotBuilder().build(
        {"nodes": [make_node("a", extra={"x": 2})], "edges": []},
        meta=meta,
    )

    d = DefaultSnapshotDiffEngine().diff(before, after, include_details=True)
    assert d.nodes_added == 0
    assert d.nodes_removed == 0
    # changed nodes live in details only (counts are add/remove)
    assert len(d.details["nodes"]["changed"]) == 1


def test_diff_include_details_false(meta):
    from pacta.snapshot.builder import DefaultSnapshotBuilder
    from pacta.snapshot.diff import DefaultSnapshotDiffEngine

    before = DefaultSnapshotBuilder().build({"nodes": [make_node("a")], "edges": []}, meta=meta)
    after = DefaultSnapshotBuilder().build({"nodes": [make_node("a"), make_node("b")], "edges": []}, meta=meta)

    d = DefaultSnapshotDiffEngine().diff(before, after, include_details=False)
    assert d.nodes_added == 1
    assert d.details == {}  # explicitly empty when include_details=False


@dataclass(frozen=True, slots=True)
class ObjViolation:
    violation_key: str
    status: str = "unknown"


def test_baseline_marks_new_and_existing_and_counts_fixed():
    from pacta.snapshot.baseline import DefaultBaselineService

    svc = DefaultBaselineService()

    baseline = {"violations": [{"violation_key": "A"}, {"violation_key": "B"}]}
    current = [{"violation_key": "B"}, {"violation_key": "C"}]

    marked, result = svc.mark_relative_to_baseline(current, baseline)

    assert {v["violation_key"]: v["status"] for v in marked} == {"B": "existing", "C": "new"}
    assert result.new == 1
    assert result.existing == 1
    assert result.fixed == 1  # "A" is fixed (present in baseline, absent now)
    assert result.unknown == 0


def test_baseline_supports_list_baseline():
    from pacta.snapshot.baseline import DefaultBaselineService

    svc = DefaultBaselineService()

    baseline = [{"violation_key": "A"}]
    current = [{"violation_key": "A"}, {"violation_key": "B"}]

    marked, result = svc.mark_relative_to_baseline(current, baseline)
    assert marked[0]["status"] == "existing"
    assert marked[1]["status"] == "new"
    assert result.fixed == 0


def test_baseline_marks_unknown_when_key_missing():
    from pacta.snapshot.baseline import DefaultBaselineService

    svc = DefaultBaselineService()

    baseline = {"violations": [{"violation_key": "A"}]}
    current = [{"no_key_here": 123}]

    marked, result = svc.mark_relative_to_baseline(current, baseline)
    assert marked[0]["status"] == "unknown"
    assert result.unknown == 1
    assert result.new == 0
    assert result.existing == 0


def test_baseline_supports_object_violations_dataclass():
    from pacta.snapshot.baseline import DefaultBaselineService

    svc = DefaultBaselineService()

    baseline = {"violations": [ObjViolation("A")]}
    current = [ObjViolation("A"), ObjViolation("B")]

    marked, result = svc.mark_relative_to_baseline(current, baseline)

    # Because ObjViolation is frozen, service returns replaced copies
    assert isinstance(marked[0], ObjViolation)
    assert marked[0].status == "existing"
    assert marked[1].status == "new"
    assert result.fixed == 0


def test_baseline_key_fn_override():
    from pacta.snapshot.baseline import DefaultBaselineService

    svc = DefaultBaselineService()

    baseline = {"violations": [{"k": "A"}]}
    current = [{"k": "A"}, {"k": "B"}]

    def key_fn(v: Mapping[str, Any]) -> str:
        return str(v["k"])

    marked, result = svc.mark_relative_to_baseline(current, baseline, key_fn=key_fn)
    assert marked[0]["status"] == "existing"
    assert marked[1]["status"] == "new"
    assert result.fixed == 0


def test_baseline_none_or_empty_baseline():
    from pacta.snapshot.baseline import DefaultBaselineService

    svc = DefaultBaselineService()

    current = [{"violation_key": "A"}]

    marked1, result1 = svc.mark_relative_to_baseline(current, None)
    assert marked1[0]["status"] == "new"
    assert result1.fixed == 0

    marked2, result2 = svc.mark_relative_to_baseline(current, {"violations": []})
    assert marked2[0]["status"] == "new"
    assert result2.fixed == 0
