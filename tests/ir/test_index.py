from pathlib import Path

from pacta.ir.index import build_index
from pacta.ir.types import (
    ArchitectureIR,
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


def cid(fqname: str, *, code_root: str = "repo", lang: Language = Language.PYTHON) -> CanonicalId:
    return CanonicalId(language=lang, code_root=code_root, fqname=fqname)


def node(
    fqname: str,
    *,
    kind: SymbolKind = SymbolKind.MODULE,
    path: str | None = None,
    name: str | None = None,
    container: str | None = None,
    layer: str | None = None,
    context: str | None = None,
) -> IRNode:
    return IRNode(
        id=cid(fqname),
        kind=kind,
        name=name,
        path=path,
        loc=None,
        container=container,
        layer=layer,
        context=context,
        tags=(),
        attributes={},
    )


def edge(
    src_fq: str,
    dst_fq: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    loc_file: str | None = None,
    loc_line: int = 1,
    loc_col: int = 1,
) -> IREdge:
    loc = None
    if loc_file is not None:
        loc = SourceLoc(file=loc_file, start=SourcePos(line=loc_line, column=loc_col))
    return IREdge(
        src=cid(src_fq),
        dst=cid(dst_fq),
        dep_type=dep_type,
        loc=loc,
        confidence=1.0,
        details={},
        src_container=None,
        src_layer=None,
        src_context=None,
        dst_container=None,
        dst_layer=None,
        dst_context=None,
    )


def mk_ir(nodes: list[IRNode], edges: list[IREdge]) -> ArchitectureIR:
    return ArchitectureIR(
        schema_version=1,
        produced_by="test",
        repo_root=str(Path(".").resolve()),
        nodes=tuple(nodes),
        edges=tuple(edges),
        metadata={},
    )


# Tests


def test_build_index_empty_ir():
    ir = mk_ir(nodes=[], edges=[])
    idx = build_index(ir)

    assert idx.nodes_by_id == {}
    assert idx.nodes_by_kind == {}
    assert idx.nodes_by_container == {}
    assert idx.nodes_by_layer == {}
    assert idx.nodes_by_context == {}

    assert idx.edges == ()
    assert idx.edges_by_type == {}
    assert idx.out_edges_by_src == {}
    assert idx.in_edges_by_dst == {}

    # convenience methods should return empty safely
    assert idx.get_node("python://repo::x") is None
    assert idx.out_edges("python://repo::x") == ()
    assert idx.in_edges("python://repo::x") == ()
    assert idx.nodes_in_container("any") == ()
    assert idx.nodes_in_layer("any") == ()
    assert idx.nodes_in_context("any") == ()


def test_nodes_by_id_and_get_node_supports_str_and_canonicalid():
    n1 = node("a.b", kind=SymbolKind.MODULE, path="a/b.py")
    ir = mk_ir(nodes=[n1], edges=[])
    idx = build_index(ir)

    key = str(n1.id)
    assert idx.nodes_by_id[key] == n1
    assert idx.get_node(key) == n1
    assert idx.get_node(n1.id) == n1


def test_nodes_grouped_by_kind_container_layer_context_sorted_deterministically():
    # Intentionally shuffled input order
    n1 = node("pkg.z", kind=SymbolKind.MODULE, path="z.py", container="c1", layer="domain", context="ctx")
    n2 = node("pkg.a", kind=SymbolKind.MODULE, path="a.py", container="c1", layer="domain", context="ctx")
    n3 = node("pkg.m", kind=SymbolKind.CLASS, path="m.py", container="c2", layer="infra", context="ctx2")
    n4 = node("pkg.b", kind=SymbolKind.MODULE, path="b.py")  # no container/layer/context

    ir = mk_ir(nodes=[n1, n2, n3, n4], edges=[])
    idx = build_index(ir)

    # grouped by kind
    assert SymbolKind.MODULE in idx.nodes_by_kind
    assert SymbolKind.CLASS in idx.nodes_by_kind

    # determinism: modules should be sorted by (kind, id, path, name)
    modules = idx.nodes_by_kind[SymbolKind.MODULE]
    assert [str(n.id) for n in modules] == sorted([str(n2.id), str(n1.id), str(n4.id)])

    # group by container/layer/context should include only nodes that have those fields
    assert idx.nodes_by_container["c1"] == tuple(
        sorted([n1, n2], key=lambda x: (x.kind.value, str(x.id), x.path or "", x.name or ""))
    )
    assert idx.nodes_by_layer["domain"] == tuple(
        sorted([n1, n2], key=lambda x: (x.kind.value, str(x.id), x.path or "", x.name or ""))
    )
    assert idx.nodes_by_context["ctx"] == tuple(
        sorted([n1, n2], key=lambda x: (x.kind.value, str(x.id), x.path or "", x.name or ""))
    )

    assert idx.nodes_by_container["c2"] == (n3,)
    assert idx.nodes_by_layer["infra"] == (n3,)
    assert idx.nodes_by_context["ctx2"] == (n3,)

    # nodes without these fields should not appear in those maps
    assert "unknown" not in idx.nodes_by_container
    assert "unknown" not in idx.nodes_by_layer
    assert "unknown" not in idx.nodes_by_context


def test_edges_sorted_deterministically_by_type_src_dst_and_location():
    # Same dep_type/src/dst but different location -> location participates in sort key
    e1 = edge("a", "b", dep_type=DepType.IMPORT, loc_file="x.py", loc_line=10, loc_col=2)
    e2 = edge("a", "b", dep_type=DepType.IMPORT, loc_file="x.py", loc_line=2, loc_col=1)
    e3 = edge("a", "c", dep_type=DepType.IMPORT, loc_file="a.py", loc_line=1, loc_col=1)
    e4 = edge("a", "b", dep_type=DepType.REQUIRE, loc_file=None)  # different type, no loc

    ir = mk_ir(nodes=[], edges=[e1, e2, e3, e4])
    idx = build_index(ir)

    # Verify global edge sorting matches edge_sort_key behavior
    # Order by dep_type, src, dst, loc(file,line,col)
    expected = sorted(
        [e1, e2, e3, e4],
        key=lambda e: (
            e.dep_type.value,
            str(e.src),
            str(e.dst),
            ("", 0, 0) if e.loc is None else (e.loc.file, e.loc.start.line, e.loc.start.column),
        ),
    )
    assert list(idx.edges) == expected


def test_edges_by_type_and_adjacency_lists():
    nA = node("A", path="A.py")
    nB = node("B", path="B.py")
    nC = node("C", path="C.py")

    eAB = edge("A", "B", dep_type=DepType.IMPORT, loc_file="A.py", loc_line=1)
    eAC = edge("A", "C", dep_type=DepType.IMPORT, loc_file="A.py", loc_line=2)
    eBA = edge("B", "A", dep_type=DepType.REQUIRE, loc_file="B.py", loc_line=5)

    ir = mk_ir(nodes=[nA, nB, nC], edges=[eAC, eBA, eAB])  # shuffled
    idx = build_index(ir)

    # edges_by_type
    assert DepType.IMPORT in idx.edges_by_type
    assert DepType.REQUIRE in idx.edges_by_type

    edges_with_type_import = idx.edges_by_type[DepType.IMPORT]
    assert len(edges_with_type_import) == 2
    assert eAB in edges_with_type_import and eAC in edges_with_type_import
    assert idx.edges_by_type[DepType.REQUIRE] == (eBA,)

    # adjacency: out edges
    A_key = str(nA.id)
    B_key = str(nB.id)
    C_key = str(nC.id)

    out_A = idx.out_edges(A_key)
    assert len(out_A) == 2
    assert eAB in out_A and eAC in out_A
    assert idx.out_edges(B_key) == (eBA,)
    assert idx.out_edges(C_key) == ()

    # adjacency: in edges
    in_A = idx.in_edges(A_key)
    assert in_A == (eBA,)
    assert idx.in_edges(B_key) == (eAB,)
    assert idx.in_edges(C_key) == (eAC,)


def test_adjacency_contains_edges_even_if_nodes_missing():
    # IR may contain edges to nodes that are not in ir.nodes (common for external deps).
    e = edge("local.mod", "external.lib", dep_type=DepType.IMPORT, loc_file="local.py", loc_line=1)
    ir = mk_ir(nodes=[node("local.mod", path="local.py")], edges=[e])

    idx = build_index(ir)

    assert idx.out_edges(str(cid("local.mod"))) == (e,)
    assert idx.in_edges(str(cid("external.lib"))) == (e,)


def test_duplicate_node_ids_last_wins_in_nodes_by_id_but_groupings_include_both():
    # This is an important edge case given build_index implementation:
    # - nodes_by_id uses overwrite assignment
    # - groupings iterate over ir.nodes and will include both entries
    n_old = node("dup", kind=SymbolKind.MODULE, path="old.py", container="c1")
    n_new = node("dup", kind=SymbolKind.MODULE, path="new.py", container="c1")

    ir = mk_ir(nodes=[n_old, n_new], edges=[])
    idx = build_index(ir)

    # last assignment wins
    assert idx.get_node(str(n_old.id)) == n_new

    # grouping includes both, then sorts them
    grouped = idx.nodes_in_container("c1")

    assert len(grouped) == 2
    assert n_old in grouped and n_new in grouped


def test_nodes_in_helpers_return_empty_for_unknown_group():
    ir = mk_ir(
        nodes=[node("x", container="c1", layer="domain", context="ctx")],
        edges=[],
    )
    idx = build_index(ir)

    assert idx.nodes_in_container("does-not-exist") == ()
    assert idx.nodes_in_layer("does-not-exist") == ()
    assert idx.nodes_in_context("does-not-exist") == ()


def test_out_in_helpers_return_empty_for_unknown_node():
    ir = mk_ir(nodes=[node("x")], edges=[])
    idx = build_index(ir)

    assert idx.out_edges("python://repo::missing") == ()
    assert idx.in_edges("python://repo::missing") == ()


def test_edges_map_keys_are_canonicalid_strings():
    n1 = node("a")
    n2 = node("b")
    e = edge("a", "b", dep_type=DepType.IMPORT, loc_file="a.py", loc_line=1)
    ir = mk_ir(nodes=[n1, n2], edges=[e])
    idx = build_index(ir)

    assert str(n1.id) in idx.out_edges_by_src
    assert str(n2.id) in idx.in_edges_by_dst
