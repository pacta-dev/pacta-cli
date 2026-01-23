import pytest
from pacta.ir.normalize import DefaultIRNormalizer
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


def cid(fqname: str, *, code_root: str = "repo") -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=fqname)


def node(
    fqname: str,
    *,
    kind: SymbolKind = SymbolKind.MODULE,
    path: str | None = None,
    loc_file: str | None = None,
    loc_line: int = 1,
    loc_col: int = 1,
    tags: tuple[str, ...] = (),
    attributes: dict | None = None,
    container: str | None = None,
    layer: str | None = None,
    context: str | None = None,
    name: str | None = None,
) -> IRNode:
    loc = None
    if loc_file is not None:
        loc = SourceLoc(file=loc_file, start=SourcePos(line=loc_line, column=loc_col))
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
    loc_file: str | None = None,
    loc_line: int = 1,
    loc_col: int = 1,
    confidence: float = 1.0,
    details: dict | None = None,
    # enrichment fields (should not affect normalization except ordering key)
    src_container: str | None = None,
    src_layer: str | None = None,
    src_context: str | None = None,
    dst_container: str | None = None,
    dst_layer: str | None = None,
    dst_context: str | None = None,
) -> IREdge:
    loc = None
    if loc_file is not None:
        loc = SourceLoc(file=loc_file, start=SourcePos(line=loc_line, column=loc_col))
    return IREdge(
        src=cid(src_fq),
        dst=cid(dst_fq),
        dep_type=dep_type,
        loc=loc,
        confidence=confidence,
        details=details or {},
        src_container=src_container,
        src_layer=src_layer,
        src_context=src_context,
        dst_container=dst_container,
        dst_layer=dst_layer,
        dst_context=dst_context,
    )


def mk_ir(
    nodes: list[IRNode],
    edges: list[IREdge],
    *,
    repo_root: str = ".",
    produced_by: str = "test",
    schema_version: int = 1,
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


def test_normalize_repo_root_path_normalization():
    ir = mk_ir(nodes=[], edges=[], repo_root=r".\repo\//sub")
    out = DefaultIRNormalizer().normalize(ir)
    assert out.repo_root == "repo/sub"


def test_normalize_node_path_normalization_backslashes_dot_slashes_and_double_slashes():
    n = node("x", path=r".\a\b\//c.py")
    ir = mk_ir(nodes=[n], edges=[])
    out = DefaultIRNormalizer().normalize(ir)

    assert out.nodes[0].path == "a/b/c.py"


def test_normalize_edge_location_file_path_normalization():
    e = edge("a", "b", loc_file=r".\src\//mod.py", loc_line=10, loc_col=2)
    ir = mk_ir(nodes=[], edges=[e])
    out = DefaultIRNormalizer().normalize(ir)

    assert out.edges[0].loc is not None
    assert out.edges[0].loc.file == "src/mod.py"
    assert out.edges[0].loc.start.line == 10
    assert out.edges[0].loc.start.column == 2


def test_normalize_location_coerces_line_col_to_int():
    # even if someone built SourcePos with ints, this ensures int coercion doesn't break
    e = edge("a", "b", loc_file="x.py", loc_line=7, loc_col=3)
    ir = mk_ir(nodes=[], edges=[e])
    out = DefaultIRNormalizer().normalize(ir)

    assert isinstance(out.edges[0].loc.start.line, int)
    assert isinstance(out.edges[0].loc.start.column, int)


def test_normalize_node_tags_strip_dedupe_sort():
    n = node("x", tags=("  a", "b", "a", "", "  ", "c  "))
    ir = mk_ir(nodes=[n], edges=[])
    out = DefaultIRNormalizer().normalize(ir)

    assert out.nodes[0].tags == ("a", "b", "c")


def test_normalize_node_attributes_mapping_sorted_and_recursive():
    attrs = {
        "b": 2,
        "a": {"d": 4, "c": 3},
        "c": [{"z": 1, "y": 0}, 5],
    }
    n = node("x", attributes=attrs)
    ir = mk_ir(nodes=[n], edges=[])
    out = DefaultIRNormalizer().normalize(ir)

    norm_attrs = out.nodes[0].attributes
    assert list(norm_attrs.keys()) == ["a", "b", "c"]
    assert list(norm_attrs["a"].keys()) == ["c", "d"]
    assert isinstance(norm_attrs["c"], list)
    assert list(norm_attrs["c"][0].keys()) == ["y", "z"]


def test_normalize_edge_details_mapping_sorted_and_recursive():
    details = {"b": 2, "a": {"d": 4, "c": 3}}
    e = edge("a", "b", details=details)
    ir = mk_ir(nodes=[], edges=[e])
    out = DefaultIRNormalizer().normalize(ir)

    norm_details = out.edges[0].details
    assert list(norm_details.keys()) == ["a", "b"]
    assert list(norm_details["a"].keys()) == ["c", "d"]


def test_normalize_metadata_mapping_sorted_and_recursive():
    meta = {"z": 1, "a": {"b": 2, "a": 1}}
    ir = mk_ir(nodes=[], edges=[], metadata=meta)
    out = DefaultIRNormalizer().normalize(ir)

    assert list(out.metadata.keys()) == ["a", "z"]
    assert list(out.metadata["a"].keys()) == ["a", "b"]


@pytest.mark.parametrize(
    "value,expected",
    [
        (-1.0, 0.0),
        (0.0, 0.0),
        (0.25, 0.25),
        (1.0, 1.0),
        (2.0, 1.0),
    ],
)
def test_normalize_edge_confidence_clamped(value, expected):
    e = edge("a", "b", confidence=value)
    ir = mk_ir(nodes=[], edges=[e])
    out = DefaultIRNormalizer().normalize(ir)

    assert out.edges[0].confidence == expected


def test_normalize_edge_confidence_nan_becomes_zero():
    e = edge("a", "b", confidence=float("nan"))
    ir = mk_ir(nodes=[], edges=[e])
    out = DefaultIRNormalizer().normalize(ir)

    assert out.edges[0].confidence == 0.0


def test_normalize_preserves_schema_version_and_produced_by_as_strings():
    ir = mk_ir(nodes=[], edges=[], produced_by="plug@1.2.3", schema_version=7)
    out = DefaultIRNormalizer().normalize(ir)

    assert out.schema_version == 7
    assert out.produced_by == "plug@1.2.3"


def test_normalize_sorts_nodes_deterministically_by_kind_then_id_then_path_then_name_then_enrichment():
    # Create nodes out of order with different sort-key fields
    n1 = node("b", kind=SymbolKind.MODULE, path="b.py", name="B")
    n2 = node("a", kind=SymbolKind.MODULE, path="a.py", name="A")
    n3 = node("a", kind=SymbolKind.CLASS, path="a.py", name="AClass")
    n4 = node("a", kind=SymbolKind.MODULE, path="a.py", name="A", container="c", layer="domain", context="ctx")

    ir = mk_ir(nodes=[n1, n3, n4, n2], edges=[])
    out = DefaultIRNormalizer().normalize(ir)

    # Must be sorted by:
    # (kind.value, str(id), path, name, container, layer, context)
    ids = [
        (n.kind.value, str(n.id), n.path or "", n.name or "", n.container or "", n.layer or "", n.context or "")
        for n in out.nodes
    ]
    assert ids == sorted(ids)


def test_normalize_sorts_edges_deterministically_by_type_src_dst_location_and_enrichment_fields():
    e1 = edge("a", "b", dep_type=DepType.REQUIRE, loc_file="x.py", loc_line=2)
    e2 = edge("a", "b", dep_type=DepType.IMPORT, loc_file="x.py", loc_line=10)
    e3 = edge("a", "c", dep_type=DepType.IMPORT, loc_file="a.py", loc_line=1)
    e4 = edge("a", "b", dep_type=DepType.IMPORT, loc_file="x.py", loc_line=2, src_container="c1")

    ir = mk_ir(nodes=[], edges=[e1, e2, e3, e4])
    out = DefaultIRNormalizer().normalize(ir)

    def sort_key(e: IREdge):
        loc = e.loc
        loc_key = ("", 0, 0) if loc is None else (loc.file, loc.start.line, loc.start.column)
        return (
            e.dep_type.value,
            str(e.src),
            str(e.dst),
            loc_key,
            e.src_container or "",
            e.src_layer or "",
            e.src_context or "",
            e.dst_container or "",
            e.dst_layer or "",
            e.dst_context or "",
        )

    assert list(out.edges) == sorted(list(out.edges), key=sort_key)


def test_normalize_does_not_drop_nodes_or_edges():
    n = node("x", path="x.py", tags=("t",))
    e = edge("x", "y", dep_type=DepType.IMPORT, details={"k": "v"}, confidence=0.5)
    ir = mk_ir(nodes=[n], edges=[e])

    out = DefaultIRNormalizer().normalize(ir)

    assert len(out.nodes) == 1
    assert len(out.edges) == 1
    assert str(out.nodes[0].id) == str(n.id)
    assert str(out.edges[0].src) == str(e.src)
    assert str(out.edges[0].dst) == str(e.dst)


def test_normalize_is_idempotent():
    n = node("x", path=r".\a\b.py", tags=(" a", "a", "b "), attributes={"b": 2, "a": 1})
    e = edge("x", "y", loc_file=r".\a\c.py", loc_line=1, details={"b": 2, "a": 1}, confidence=2.0)
    ir = mk_ir(nodes=[n], edges=[e], repo_root=r".\repo\//sub", metadata={"z": 1, "a": {"b": 2, "a": 1}})

    normalizer = DefaultIRNormalizer()
    out1 = normalizer.normalize(ir)
    out2 = normalizer.normalize(out1)

    # dataclasses are frozen but compare by value
    assert out1 == out2
