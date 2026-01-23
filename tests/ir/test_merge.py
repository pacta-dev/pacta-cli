import pytest
from pacta.ir.keys import edge_key
from pacta.ir.merge import DefaultIRMerger
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


def cid(fqname: str, *, produced_by: str = "repo", code_root: str = "repo") -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=fqname)


def node(
    fqname: str,
    *,
    kind: SymbolKind = SymbolKind.MODULE,
    path: str | None = None,
    name: str | None = None,
    has_loc: bool = False,
    attributes: dict | None = None,
    tags: tuple[str, ...] = (),
    container: str | None = None,
    layer: str | None = None,
    context: str | None = None,
) -> IRNode:
    loc = None
    if has_loc:
        loc = SourceLoc(file=path or "x.py", start=SourcePos(line=1, column=1))
    return IRNode(
        id=cid(fqname),
        kind=kind,
        name=name,
        path=path,
        loc=loc,
        container=container,
        layer=layer,
        context=context,
        tags=tags,
        attributes=attributes or {},
    )


def edge(
    src_fq: str,
    dst_fq: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    confidence: float = 1.0,
    has_loc: bool = False,
    details: dict | None = None,
    src_container: str | None = None,
    dst_container: str | None = None,
) -> IREdge:
    loc = None
    if has_loc:
        loc = SourceLoc(file="x.py", start=SourcePos(line=1, column=1))
    return IREdge(
        src=cid(src_fq),
        dst=cid(dst_fq),
        dep_type=dep_type,
        loc=loc,
        confidence=confidence,
        details=details or {},
        src_container=src_container,
        src_layer=None,
        src_context=None,
        dst_container=dst_container,
        dst_layer=None,
        dst_context=None,
    )


def mk_ir(
    *,
    produced_by: str,
    nodes: list[IRNode],
    edges: list[IREdge],
    schema_version: int = 1,
    repo_root: str = "REPO",
    metadata: dict | None = None,
) -> ArchitectureIR:
    return ArchitectureIR(
        schema_version=schema_version,
        produced_by=produced_by,
        repo_root=repo_root,
        nodes=tuple(nodes),
        edges=tuple(edges),
        metadata=metadata or {},
    )


# Tests


def test_merge_requires_at_least_one_ir():
    merger = DefaultIRMerger()
    with pytest.raises(ValueError):
        merger.merge([])


def test_merge_basic_unions_nodes_and_edges():
    ir1 = mk_ir(
        produced_by="a1",
        nodes=[node("A"), node("B")],
        edges=[edge("A", "B")],
    )
    ir2 = mk_ir(
        produced_by="a2",
        nodes=[node("C")],
        edges=[edge("B", "C")],
    )

    merged = DefaultIRMerger().merge([ir1, ir2])

    assert {str(n.id) for n in merged.nodes} == {str(cid("A")), str(cid("B")), str(cid("C"))}
    assert {edge_key(e) for e in merged.edges} == {edge_key(edge("A", "B")), edge_key(edge("B", "C"))}
    assert merged.produced_by == "pacta-merged"


def test_merge_schema_version_is_max():
    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[], schema_version=1)
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[], schema_version=3)

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.schema_version == 3


def test_merge_repo_root_prefers_first_ir():
    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[], repo_root="/repo/one")
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[], repo_root="/repo/two")

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.repo_root == "/repo/one"


def test_merge_dedupes_nodes_by_canonical_id_and_prefers_richer_node():
    # same node id, one has more info (path + loc)
    n_poor = node("X", path=None, has_loc=False)
    n_rich = node("X", path="x.py", has_loc=True, name="X")

    ir1 = mk_ir(produced_by="a1", nodes=[n_poor], edges=[])
    ir2 = mk_ir(produced_by="a2", nodes=[n_rich], edges=[])

    merged = DefaultIRMerger().merge([ir1, ir2])

    assert len(merged.nodes) == 1
    chosen = merged.nodes[0]
    assert chosen.path == "x.py"
    assert chosen.loc is not None
    assert chosen.name == "X"


def test_merge_node_tie_break_is_deterministic_keep_first_when_equal():
    n1 = node("X", path="x.py", has_loc=True)
    n2 = node("X", path="x.py", has_loc=True)  # equal score

    ir1 = mk_ir(produced_by="a1", nodes=[n1], edges=[])
    ir2 = mk_ir(produced_by="a2", nodes=[n2], edges=[])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.nodes[0] == n1


def test_merge_dedupes_edges_by_default_identity_src_dst_type():
    # same src/dst/type but different location => should dedupe (since include_location=False)
    e1 = edge("A", "B", dep_type=DepType.IMPORT, has_loc=True)
    e2 = edge("A", "B", dep_type=DepType.IMPORT, has_loc=False)

    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[e1])
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[e2])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert len(merged.edges) == 1
    assert edge_key(merged.edges[0]) == edge_key(e1)


def test_merge_prefers_edge_with_higher_confidence():
    e_low = edge("A", "B", confidence=0.2, has_loc=False)
    e_high = edge("A", "B", confidence=0.9, has_loc=False)

    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[e_low])
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[e_high])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.edges[0].confidence == 0.9


def test_merge_prefers_edge_with_location_when_confidence_equal():
    e_noloc = edge("A", "B", confidence=1.0, has_loc=False)
    e_loc = edge("A", "B", confidence=1.0, has_loc=True)

    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[e_noloc])
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[e_loc])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.edges[0].loc is not None


def test_merge_prefers_edge_with_more_details_when_other_equal():
    e_few = edge("A", "B", details={"a": 1})
    e_more = edge("A", "B", details={"a": 1, "b": 2})

    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[e_few])
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[e_more])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.edges[0].details == {"a": 1, "b": 2}


def test_merge_prefers_edge_with_enriched_fields_when_other_equal():
    e_plain = edge("A", "B")
    e_enriched = edge("A", "B", src_container="c1", dst_container="c2")

    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[e_plain])
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[e_enriched])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.edges[0].src_container == "c1"
    assert merged.edges[0].dst_container == "c2"


def test_merge_edge_tie_break_is_deterministic_keep_first_when_equal():
    e1 = edge("A", "B", confidence=1.0, has_loc=True, details={"a": 1})
    e2 = edge("A", "B", confidence=1.0, has_loc=True, details={"a": 1})

    ir1 = mk_ir(produced_by="a1", nodes=[], edges=[e1])
    ir2 = mk_ir(produced_by="a2", nodes=[], edges=[e2])

    merged = DefaultIRMerger().merge([ir1, ir2])
    assert merged.edges[0] == e1


def test_merge_metadata_contains_base_and_sources_namespaced():
    ir1 = mk_ir(produced_by="plugA", nodes=[], edges=[], metadata={"x": 1, "shared": "a"})
    ir2 = mk_ir(produced_by="plugB", nodes=[], edges=[], metadata={"y": 2, "shared": "b"})

    merged = DefaultIRMerger().merge([ir1, ir2])

    assert "base" in merged.metadata
    assert merged.metadata["base"] == {"x": 1, "shared": "a"}

    assert "sources" in merged.metadata
    assert merged.metadata["sources"]["plugA"] == {"x": 1, "shared": "a"}
    assert merged.metadata["sources"]["plugB"] == {"y": 2, "shared": "b"}


def test_merge_metadata_disambiguates_duplicate_produced_by_names():
    ir1 = mk_ir(produced_by="same", nodes=[], edges=[], metadata={"a": 1})
    ir2 = mk_ir(produced_by="same", nodes=[], edges=[], metadata={"b": 2})
    ir3 = mk_ir(produced_by="same", nodes=[], edges=[], metadata={"c": 3})

    merged = DefaultIRMerger().merge([ir1, ir2, ir3])

    sources = merged.metadata["sources"]
    assert "same" in sources
    assert "same#2" in sources
    assert "same#3" in sources

    assert sources["same"] == {"a": 1}
    assert sources["same#2"] == {"b": 2}
    assert sources["same#3"] == {"c": 3}


def test_merge_is_deterministic_wrt_input_order_for_conflict_resolution():
    # because tie-break is "keep first when equal", the chosen node/edge depends on order
    # BUT within a given order, output must be stable and reflect the policy.
    n1 = node("X", path="a.py", has_loc=True)
    n2 = node("X", path="a.py", has_loc=True)  # equal score
    ir1 = mk_ir(produced_by="a1", nodes=[n1], edges=[])
    ir2 = mk_ir(produced_by="a2", nodes=[n2], edges=[])

    merged_12 = DefaultIRMerger().merge([ir1, ir2])
    merged_21 = DefaultIRMerger().merge([ir2, ir1])

    assert merged_12.nodes[0] == n1
    assert merged_21.nodes[0] == n2
