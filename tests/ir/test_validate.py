import pytest
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
from pacta.ir.validate import IRValidationOptions, validate_ir

# Helpers


def cid(fqname: str, *, code_root: str = "repo") -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root=code_root, fqname=fqname)


def node(fqname: str, *, kind: SymbolKind = SymbolKind.MODULE) -> IRNode:
    return IRNode(
        id=cid(fqname),
        kind=kind,
        name=None,
        path=None,
        loc=None,
        container=None,
        layer=None,
        context=None,
        tags=(),
        attributes={},
    )


def edge(
    src_fq: str,
    dst_fq: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    confidence: float = 1.0,
    loc: SourceLoc | None = None,
) -> IREdge:
    return IREdge(
        src=cid(src_fq),
        dst=cid(dst_fq),
        dep_type=dep_type,
        loc=loc,
        confidence=confidence,
        details={},
        src_container=None,
        src_layer=None,
        src_context=None,
        dst_container=None,
        dst_layer=None,
        dst_context=None,
    )


def loc(file: str, line: int, col: int = 1, *, end_line: int | None = None, end_col: int | None = None) -> SourceLoc:
    return SourceLoc(
        file=file,
        start=SourcePos(line=line, column=col),
        end=None if end_line is None else SourcePos(line=end_line, column=end_col or 1),
    )


def mk_ir(
    *,
    schema_version: int = 1,
    nodes: list[IRNode] = None,
    edges: list[IREdge] = None,
) -> ArchitectureIR:
    return ArchitectureIR(
        schema_version=schema_version,
        produced_by="test",
        repo_root="repo",
        nodes=tuple(nodes or []),
        edges=tuple(edges or []),
        metadata={},
    )


# Tests


def test_validate_ir_ok_returns_empty_list():
    ir = mk_ir(nodes=[node("a"), node("b")], edges=[edge("a", "b")])
    errors = validate_ir(ir)
    assert errors == []


def test_validate_ir_invalid_schema_version():
    ir = mk_ir(schema_version=0, nodes=[], edges=[])
    errors = validate_ir(ir)
    assert any(e.message.startswith("Invalid IR schema_version") for e in errors)
    assert any(e.type == "runtime_error" for e in errors)


def test_validate_ir_max_nodes_guard():
    ir = mk_ir(nodes=[node("a"), node("b")], edges=[])
    errors = validate_ir(ir, opts=IRValidationOptions(max_nodes=1))
    assert any("too many nodes" in e.message.lower() for e in errors)


def test_validate_ir_max_edges_guard():
    ir = mk_ir(nodes=[node("a"), node("b")], edges=[edge("a", "b"), edge("b", "a")])
    errors = validate_ir(ir, opts=IRValidationOptions(max_edges=1))
    assert any("too many edges" in e.message.lower() for e in errors)


def test_validate_ir_duplicate_node_ids_detected():
    n1 = node("dup")
    n2 = node("dup")  # same canonical id
    ir = mk_ir(nodes=[n1, n2], edges=[])
    errors = validate_ir(ir)

    assert any("Duplicate IR node id detected" in e.message for e in errors)


def test_validate_ir_node_empty_canonical_id_detected():
    # Create a CanonicalId that stringifies to empty via empty fields
    empty = CanonicalId(language=Language.UNKNOWN, code_root="", fqname="")
    n = IRNode(
        id=empty,
        kind=SymbolKind.MODULE,
        name=None,
        path=None,
        loc=None,
        container=None,
        layer=None,
        context=None,
        tags=(),
        attributes={},
    )
    ir = mk_ir(nodes=[n], edges=[])
    errors = validate_ir(ir)

    assert any("empty canonical id" in e.message.lower() for e in errors)


@pytest.mark.parametrize(
    "confidence",
    [-0.1, 1.1, 999.0],
)
def test_validate_ir_edge_confidence_out_of_range(confidence):
    e = edge("a", "b", confidence=confidence, loc=loc("x.py", 10, 2))
    ir = mk_ir(nodes=[node("a"), node("b")], edges=[e])
    errors = validate_ir(ir)

    assert any("confidence must be within [0,1]" in err.message for err in errors)
    # Location should be mapped
    err = next(err for err in errors if "confidence must be within [0,1]" in err.message)
    assert err.location is not None
    assert err.location.file == "x.py"
    assert err.location.line == 10
    assert err.location.column == 2


def test_validate_ir_edge_confidence_nan_is_error():
    e = edge("a", "b", confidence=float("nan"))
    ir = mk_ir(nodes=[node("a"), node("b")], edges=[e])
    errors = validate_ir(ir)

    assert any("confidence must be within [0,1]" in err.message for err in errors)


def test_validate_ir_edge_empty_src_or_dst_detected():
    empty = CanonicalId(language=Language.UNKNOWN, code_root="", fqname="")
    bad_edge = IREdge(
        src=empty,
        dst=cid("b"),
        dep_type=DepType.IMPORT,
        loc=None,
        confidence=1.0,
        details={},
        src_container=None,
        src_layer=None,
        src_context=None,
        dst_container=None,
        dst_layer=None,
        dst_context=None,
    )
    ir = mk_ir(nodes=[node("b")], edges=[bad_edge])
    errors = validate_ir(ir)

    assert any("empty src or dst" in e.message.lower() for e in errors)


def test_validate_ir_strict_references_requires_nodes_for_edges():
    # Edge points to missing dst node
    ir = mk_ir(nodes=[node("a")], edges=[edge("a", "missing")])

    # non-strict => no error
    errors_non_strict = validate_ir(ir, opts=IRValidationOptions(strict_references=False))
    assert not any("strict mode" in e.message.lower() for e in errors_non_strict)

    # strict => error
    errors_strict = validate_ir(ir, opts=IRValidationOptions(strict_references=True))
    assert any("strict mode" in e.message.lower() for e in errors_strict)


def test_validate_ir_strict_references_checks_both_src_and_dst():
    # Edge points to missing src and dst nodes
    ir = mk_ir(nodes=[], edges=[edge("missing_src", "missing_dst", loc=loc("x.py", 1, 1))])
    errors = validate_ir(ir, opts=IRValidationOptions(strict_references=True))

    err = next(e for e in errors if "strict mode" in e.message.lower())
    assert err.details.get("missing_src") is True
    assert err.details.get("missing_dst") is True
    assert err.location is not None
    assert err.location.file == "x.py"


def test_validate_ir_location_end_is_mapped_if_present():
    e = edge("a", "b", confidence=2.0, loc=loc("x.py", 10, 2, end_line=10, end_col=20))
    ir = mk_ir(nodes=[node("a"), node("b")], edges=[e])
    errors = validate_ir(ir)

    err = next(err for err in errors if "confidence must be within [0,1]" in err.message)
    assert err.location is not None
    assert err.location.end_line == 10
    assert err.location.end_column == 20
