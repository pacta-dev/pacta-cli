from pacta.ir.keys import (
    dedupe_edges,
    dedupe_nodes,
    edge_key,
    node_key,
)
from pacta.ir.types import (
    CanonicalId,
    DepType,
    IREdge,
    IRNode,
    Language,
    SourceLoc,
    SourcePos,
    SymbolKind,
)

# Helpers


def cid(fqname: str) -> CanonicalId:
    return CanonicalId(
        language=Language.PYTHON,
        code_root="repo",
        fqname=fqname,
    )


def node(fqname: str, *, path: str | None = None) -> IRNode:
    return IRNode(
        id=cid(fqname),
        kind=SymbolKind.MODULE,
        name=None,
        path=path,
        loc=None,
        container=None,
        layer=None,
        context=None,
        tags=(),
        attributes={},
    )


def edge(
    src: str,
    dst: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    loc: SourceLoc | None = None,
    details: dict | None = None,
) -> IREdge:
    return IREdge(
        src=cid(src),
        dst=cid(dst),
        dep_type=dep_type,
        loc=loc,
        confidence=1.0,
        details=details or {},
        src_container=None,
        src_layer=None,
        src_context=None,
        dst_container=None,
        dst_layer=None,
        dst_context=None,
    )


def loc(file: str, line: int, col: int = 1) -> SourceLoc:
    return SourceLoc(
        file=file,
        start=SourcePos(line=line, column=col),
    )


# node_key tests


def test_node_key_is_canonical_id_string():
    n = node("a.b.c")
    assert node_key(n) == str(n.id)


def test_node_key_ignores_path_and_enrichment():
    base = node("a.b.c", path="old.py")
    enriched = IRNode(
        id=base.id,
        kind=base.kind,
        name=base.name,
        path="new.py",
        loc=None,
        container="container-x",
        layer="domain",
        context="ctx",
        tags=("tag1",),
        attributes={"x": 1},
    )

    assert node_key(base) == node_key(enriched)


def test_node_key_is_stable_across_instances():
    n1 = node("a.b.c")
    n2 = node("a.b.c")

    assert node_key(n1) == node_key(n2)


# edge_key tests


def test_edge_key_basic_identity():
    e = edge("a", "b")
    key = edge_key(e)

    assert isinstance(key, str)
    assert len(key) > 10


def test_edge_key_depends_on_src_dst_and_dep_type():
    e1 = edge("a", "b", dep_type=DepType.IMPORT)
    e2 = edge("a", "b", dep_type=DepType.REQUIRE)
    e3 = edge("a", "c", dep_type=DepType.IMPORT)

    assert edge_key(e1) != edge_key(e2)
    assert edge_key(e1) != edge_key(e3)


def test_edge_key_ignores_location_by_default():
    e1 = edge("a", "b", loc=loc("a.py", 1))
    e2 = edge("a", "b", loc=loc("a.py", 999))

    assert edge_key(e1) == edge_key(e2)


def test_edge_key_can_include_location():
    e1 = edge("a", "b", loc=loc("a.py", 1))
    e2 = edge("a", "b", loc=loc("a.py", 2))

    assert edge_key(e1, include_location=True) != edge_key(e2, include_location=True)


def test_edge_key_ignores_details_by_default():
    e1 = edge("a", "b", details={"x": 1})
    e2 = edge("a", "b", details={"x": 2})

    assert edge_key(e1) == edge_key(e2)


def test_edge_key_can_include_details():
    e1 = edge("a", "b", details={"x": 1})
    e2 = edge("a", "b", details={"x": 2})

    assert edge_key(e1, include_details=True) != edge_key(e2, include_details=True)


def test_edge_key_details_are_order_independent():
    e1 = edge("a", "b", details={"a": 1, "b": 2})
    e2 = edge("a", "b", details={"b": 2, "a": 1})

    assert edge_key(e1, include_details=True) == edge_key(e2, include_details=True)


def test_edge_key_is_stable_across_instances():
    e1 = edge("a", "b")
    e2 = edge("a", "b")

    assert edge_key(e1) == edge_key(e2)


# dedupe_nodes tests


def test_dedupe_nodes_removes_duplicates_by_identity():
    n1 = node("a")
    n2 = node("a")
    n3 = node("b")

    result = dedupe_nodes([n1, n2, n3])

    assert result == (n1, n3)


def test_dedupe_nodes_preserves_first_occurrence():
    n1 = node("a", path="first.py")
    n2 = node("a", path="second.py")

    result = dedupe_nodes([n1, n2])

    assert result == (n1,)


def test_dedupe_nodes_handles_empty_input():
    assert dedupe_nodes([]) == ()


# dedupe_edges tests


def test_dedupe_edges_removes_duplicates_by_default_identity():
    e1 = edge("a", "b", loc=loc("a.py", 1))
    e2 = edge("a", "b", loc=loc("a.py", 999))

    result = dedupe_edges([e1, e2])

    assert result == (e1,)


def test_dedupe_edges_can_be_strict_with_location():
    e1 = edge("a", "b", loc=loc("a.py", 1))
    e2 = edge("a", "b", loc=loc("a.py", 2))

    result = dedupe_edges([e1, e2], include_location=True)

    assert result == (e1, e2)


def test_dedupe_edges_preserves_first_occurrence():
    e1 = edge("a", "b")
    e2 = edge("a", "b")

    result = dedupe_edges([e1, e2])

    assert result == (e1,)


def test_dedupe_edges_handles_empty_input():
    assert dedupe_edges([]) == ()


# Regression / stability tests


def test_edge_key_is_stable_against_mutation_of_original_object():
    e = edge("a", "b", details={"x": 1})
    key1 = edge_key(e)

    # mutate original (should not affect key)
    e.details["x"] = 999

    key2 = edge_key(e)
    assert key1 == key2


def test_edge_key_is_deterministic_across_process_like_reconstruction():
    e1 = edge("a", "b", details={"b": 2, "a": 1})
    e2 = edge("a", "b", details={"a": 1, "b": 2})

    assert edge_key(e1, include_details=True) == edge_key(e2, include_details=True)
