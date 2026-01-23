from pacta.ir.select import (
    EdgeFilter,
    NodeFilter,
    match_any_glob,
    match_glob,
    match_regex,
    select_edges,
    select_nodes,
    where,
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
    return CanonicalId(language=Language.PYTHON, code_root="repo", fqname=fqname)


def node(
    fqname: str,
    *,
    kind: SymbolKind = SymbolKind.MODULE,
    path: str | None = None,
    name: str | None = None,
    container: str | None = None,
    layer: str | None = None,
    context: str | None = None,
    tags: tuple[str, ...] = (),
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
        tags=tags,
        attributes={},
    )


def edge(
    src_fq: str,
    dst_fq: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    loc_file: str | None = None,
    loc_line: int = 1,
    src_container: str | None = None,
    src_layer: str | None = None,
    src_context: str | None = None,
    dst_container: str | None = None,
    dst_layer: str | None = None,
    dst_context: str | None = None,
) -> IREdge:
    loc = None
    if loc_file is not None:
        loc = SourceLoc(file=loc_file, start=SourcePos(line=loc_line, column=1))
    return IREdge(
        src=cid(src_fq),
        dst=cid(dst_fq),
        dep_type=dep_type,
        loc=loc,
        confidence=1.0,
        details={},
        src_container=src_container,
        src_layer=src_layer,
        src_context=src_context,
        dst_container=dst_container,
        dst_layer=dst_layer,
        dst_context=dst_context,
    )


# match_* helpers


def test_match_glob_basic_and_none():
    assert match_glob("abc.py", "*.py") is True
    assert match_glob("abc.py", "*.txt") is False
    assert match_glob(None, "*.py") is False


def test_match_glob_is_case_sensitive():
    # fnmatchcase is case-sensitive on all platforms
    assert match_glob("File.py", "file.py") is False
    assert match_glob("File.py", "File.py") is True


def test_match_any_glob():
    assert match_any_glob("a/b/c.py", ["x/*", "a/**", "*.py"]) is True
    assert match_any_glob("a/b/c.py", ["x/*", "y/*"]) is False
    assert match_any_glob(None, ["*"]) is False


def test_match_regex_basic_and_none():
    assert match_regex("services/billing/domain/a.py", r"billing/.+\.py") is True
    assert match_regex("services/billing/domain/a.py", r"scheduling") is False
    assert match_regex(None, r".*") is False


# NodeFilter.matches


def test_nodefilter_matches_kind():
    n1 = node("a", kind=SymbolKind.MODULE)
    n2 = node("b", kind=SymbolKind.CLASS)

    flt = NodeFilter(kind=SymbolKind.MODULE)
    assert flt.matches(n1) is True
    assert flt.matches(n2) is False


def test_nodefilter_matches_container_layer_context():
    n = node("a", container="c1", layer="domain", context="ctx")

    assert NodeFilter(container="c1").matches(n) is True
    assert NodeFilter(container="c2").matches(n) is False

    assert NodeFilter(layer="domain").matches(n) is True
    assert NodeFilter(layer="infra").matches(n) is False

    assert NodeFilter(context="ctx").matches(n) is True
    assert NodeFilter(context="other").matches(n) is False


def test_nodefilter_matches_path_glob_and_none_handling():
    n = node("a", path="services/billing/domain/a.py")
    assert NodeFilter(path_glob="services/**/domain/*.py").matches(n) is True
    assert NodeFilter(path_glob="services/**/infra/*.py").matches(n) is False

    n_none = node("b", path=None)
    assert NodeFilter(path_glob="*.py").matches(n_none) is False


def test_nodefilter_matches_fqname_glob():
    n = node("services.billing.domain.invoice", path="x.py")
    assert NodeFilter(fqname_glob="services.billing.domain.*").matches(n) is True
    assert NodeFilter(fqname_glob="services.scheduling.*").matches(n) is False


def test_nodefilter_matches_name_glob_and_none_handling():
    n = node("a", name="InvoiceService")
    assert NodeFilter(name_glob="*Service").matches(n) is True
    assert NodeFilter(name_glob="*Repo").matches(n) is False

    n_none = node("b", name=None)
    assert NodeFilter(name_glob="*").matches(n_none) is False


def test_nodefilter_matches_has_tag():
    n = node("a", tags=("internal", "critical"))
    assert NodeFilter(has_tag="internal").matches(n) is True
    assert NodeFilter(has_tag="missing").matches(n) is False

    n_empty = node("b", tags=())
    assert NodeFilter(has_tag="internal").matches(n_empty) is False


def test_select_nodes_preserves_input_order():
    n1 = node("a", container="c1")
    n2 = node("b", container="c1")
    n3 = node("c", container="c2")

    nodes = [n2, n1, n3]  # intentionally unsorted
    out = select_nodes(nodes, NodeFilter(container="c1"))

    assert out == (n2, n1)  # preserves input order


def test_select_nodes_without_filter_returns_all_preserving_order():
    n1 = node("a")
    n2 = node("b")
    nodes = [n2, n1]
    out = select_nodes(nodes, None)

    assert out == (n2, n1)


# EdgeFilter.matches


def test_edgefilter_matches_dep_type():
    e1 = edge("a", "b", dep_type=DepType.IMPORT)
    e2 = edge("a", "b", dep_type=DepType.REQUIRE)

    assert EdgeFilter(dep_type=DepType.IMPORT).matches(e1) is True
    assert EdgeFilter(dep_type=DepType.IMPORT).matches(e2) is False


def test_edgefilter_matches_enriched_src_dst_fields():
    e = edge(
        "a",
        "b",
        src_container="c1",
        src_layer="domain",
        src_context="ctx1",
        dst_container="c2",
        dst_layer="infra",
        dst_context="ctx2",
    )

    assert EdgeFilter(src_container="c1").matches(e) is True
    assert EdgeFilter(src_container="cX").matches(e) is False

    assert EdgeFilter(src_layer="domain").matches(e) is True
    assert EdgeFilter(dst_layer="infra").matches(e) is True
    assert EdgeFilter(dst_layer="domain").matches(e) is False

    assert EdgeFilter(src_context="ctx1").matches(e) is True
    assert EdgeFilter(dst_context="ctx2").matches(e) is True


def test_edgefilter_matches_src_dst_fqname_glob():
    e = edge("services.billing.domain.a", "services.billing.infra.db")
    assert EdgeFilter(src_fqname_glob="services.billing.domain.*").matches(e) is True
    assert EdgeFilter(dst_fqname_glob="services.billing.infra.*").matches(e) is True

    assert EdgeFilter(src_fqname_glob="services.scheduling.*").matches(e) is False


def test_edgefilter_matches_loc_file_glob_and_requires_loc():
    e_loc = edge("a", "b", loc_file="services/billing/a.py", loc_line=1)
    e_noloc = edge("a", "b", loc_file=None)

    flt = EdgeFilter(loc_file_glob="services/**/a.py")

    assert flt.matches(e_loc) is True
    assert flt.matches(e_noloc) is False


def test_select_edges_preserves_input_order():
    e1 = edge("a", "b", dep_type=DepType.IMPORT)
    e2 = edge("a", "c", dep_type=DepType.REQUIRE)
    e3 = edge("b", "c", dep_type=DepType.IMPORT)

    edges = [e3, e2, e1]  # unsorted
    out = select_edges(edges, EdgeFilter(dep_type=DepType.IMPORT))

    assert out == (e3, e1)  # preserves input order


def test_select_edges_without_filter_returns_all_preserving_order():
    e1 = edge("a", "b")
    e2 = edge("b", "c")
    edges = [e2, e1]
    out = select_edges(edges, None)

    assert out == (e2, e1)


# where() helper


def test_where_generic_filter():
    n1 = node("a", container="c1")
    n2 = node("b", container="c2")

    out = where([n1, n2], lambda n: getattr(n, "container", None) == "c1")
    assert out == (n1,)
