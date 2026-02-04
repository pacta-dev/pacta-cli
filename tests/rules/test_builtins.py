import pytest
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
from pacta.rules.builtins import (
    all_of,
    any_of,
    as_list,
    as_str,
    contains,
    get_edge_field,
    get_node_field,
    glob_match,
    in_list,
    normalize_ws,
    not_,
    regex_match,
)

# Helpers


def cid(fqname: str) -> CanonicalId:
    return CanonicalId(language=Language.PYTHON, code_root="repo", fqname=fqname)


def mk_node(
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


def mk_edge(
    src: str,
    dst: str,
    *,
    dep_type: DepType = DepType.IMPORT,
    loc_file: str | None = None,
    src_container: str | None = None,
    src_layer: str | None = None,
    src_context: str | None = None,
    dst_container: str | None = None,
    dst_layer: str | None = None,
    dst_context: str | None = None,
) -> IREdge:
    loc = None
    if loc_file is not None:
        loc = SourceLoc(file=loc_file, start=SourcePos(line=1, column=1))
    return IREdge(
        src=cid(src),
        dst=cid(dst),
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


# Value helpers


def test_as_str():
    assert as_str(None) is None
    assert as_str(123) == "123"
    assert as_str("x") == "x"


def test_as_list():
    assert as_list(None) == []
    assert as_list([1, 2]) == [1, 2]
    assert as_list((1, 2)) == [1, 2]
    assert sorted(as_list({2, 1})) == [1, 2]
    assert as_list("x") == ["x"]


def test_normalize_ws():
    assert normalize_ws(None) is None
    assert normalize_ws("  a  ") == "a"
    assert normalize_ws("") == ""


# Matchers


def test_glob_match():
    assert glob_match("a/b/c.py", "*.py") is True
    assert glob_match("a/b/c.py", "*.txt") is False
    assert glob_match(None, "*.py") is False


def test_regex_match():
    assert regex_match("services/billing/a.py", r"billing/.+\.py") is True
    assert regex_match("services/billing/a.py", r"scheduling") is False
    assert regex_match(None, r".*") is False


def test_contains_on_collections_and_strings_and_dict():
    assert contains(["a", "b"], "a") is True
    assert contains(["a", "b"], "c") is False

    assert contains(("a", "b"), "a") is True
    assert contains({"a", "b"}, "a") is True

    assert contains({"a": 1, "b": 2}, "a") is True
    assert contains({"a": 1, "b": 2}, "c") is False

    assert contains("hello world", "world") is True
    assert contains("hello world", "x") is False

    assert contains(None, "a") is False


def test_in_list_handles_list_set_tuple_and_csv_string():
    assert in_list("a", ["a", "b"]) is True
    assert in_list("c", ["a", "b"]) is False

    assert in_list("a", ("a", "b")) is True
    assert in_list("a", {"a", "b"}) is True

    assert in_list("a", "a, b, c") is True
    assert in_list("b", "a, b, c") is True
    assert in_list("d", "a, b, c") is False

    assert in_list("a", None) is False


# Field extractors


def test_get_node_field_supported_fields():
    n = mk_node(
        "services.billing.domain.invoice",
        kind=SymbolKind.CLASS,
        path="services/billing/domain/invoice.py",
        name="Invoice",
        container="billing",
        layer="domain",
        context="billing",
        tags=("internal", "critical"),
    )

    assert get_node_field(n, "symbol_kind") == SymbolKind.CLASS.value
    assert get_node_field(n, "node.symbol_kind") == SymbolKind.CLASS.value
    assert get_node_field(n, "path") == "services/billing/domain/invoice.py"
    assert get_node_field(n, "name") == "Invoice"
    assert get_node_field(n, "container") == "billing"
    assert get_node_field(n, "layer") == "domain"
    assert get_node_field(n, "context") == "billing"
    assert get_node_field(n, "tags") == ("internal", "critical")
    assert get_node_field(n, "fqname") == "services.billing.domain.invoice"
    assert get_node_field(n, "id") == str(n.id)
    assert get_node_field(n, "code_root") == "repo"
    assert get_node_field(n, "language") == Language.PYTHON.value


def test_get_node_field_unknown_raises():
    n = mk_node("a")
    with pytest.raises(KeyError):
        get_node_field(n, "unknown.field")


def test_get_edge_field_supported_fields():
    e = mk_edge(
        "services.billing.domain",
        "services.billing.infra.db",
        dep_type=DepType.IMPORT,
        loc_file="services/billing/domain/x.py",
        src_container="billing",
        src_layer="domain",
        src_context="billing",
        dst_container="billing",
        dst_layer="infra",
        dst_context="billing",
    )

    assert get_edge_field(e, "from.layer") == "domain"
    assert get_edge_field(e, "to.layer") == "infra"
    assert get_edge_field(e, "from.context") == "billing"
    assert get_edge_field(e, "to.context") == "billing"
    assert get_edge_field(e, "from.container") == "billing"
    assert get_edge_field(e, "to.container") == "billing"
    assert get_edge_field(e, "from.fqname") == "services.billing.domain"
    assert get_edge_field(e, "to.fqname") == "services.billing.infra.db"
    assert get_edge_field(e, "from.id") == str(e.src)
    assert get_edge_field(e, "to.id") == str(e.dst)
    assert get_edge_field(e, "dep.type") == DepType.IMPORT.value
    assert get_edge_field(e, "loc.file") == "services/billing/domain/x.py"


def test_get_edge_field_loc_file_returns_none_if_no_loc():
    e = mk_edge("a", "b", loc_file=None)
    assert get_edge_field(e, "loc.file") is None


def test_get_edge_field_unknown_raises():
    e = mk_edge("a", "b")
    with pytest.raises(KeyError):
        get_edge_field(e, "unknown.field")


# Predicate composition


def test_all_of_any_of_not_helpers():
    p_true = lambda _: True  # noqa: E731
    p_false = lambda _: False  # noqa: E731

    assert all_of([p_true, p_true])("x") is True
    assert all_of([p_true, p_false])("x") is False

    assert any_of([p_false, p_true])("x") is True
    assert any_of([p_false, p_false])("x") is False

    assert not_(p_true)("x") is False
    assert not_(p_false)("x") is True


# ----------------------------
# v2: New node fields (service, kind, symbol_kind)
# ----------------------------


def test_get_node_field_v2_service_and_kind():
    n = IRNode(
        id=cid("billing.api.routes"),
        kind=SymbolKind.MODULE,
        service="billing-service",
        container_kind="service",
        within="service",
    )
    assert get_node_field(n, "service") == "billing-service"
    assert get_node_field(n, "node.service") == "billing-service"
    assert get_node_field(n, "kind") == "service"
    assert get_node_field(n, "node.kind") == "service"
    assert get_node_field(n, "within") == "service"
    assert get_node_field(n, "node.within") == "service"
    assert get_node_field(n, "symbol_kind") == SymbolKind.MODULE.value


def test_get_node_field_v2_within_for_nested_container():
    """Test that 'within' differs from 'kind' for nested containers."""
    n = IRNode(
        id=cid("billing.domain.invoice.model"),
        kind=SymbolKind.MODULE,
        service="billing-service",
        container_kind="module",  # immediate container is a module
        within="service",  # top-level container is a service
    )
    assert get_node_field(n, "kind") == "module"
    assert get_node_field(n, "within") == "service"


def test_get_node_field_v2_none_when_not_enriched():
    n = IRNode(id=cid("x"), kind=SymbolKind.MODULE)
    assert get_node_field(n, "service") is None
    assert get_node_field(n, "kind") is None


# ----------------------------
# v2: New edge fields (service, kind)
# ----------------------------


def test_get_edge_field_v2_service_and_kind():
    e = IREdge(
        src=cid("a"),
        dst=cid("b"),
        dep_type=DepType.IMPORT,
        src_service="billing-service",
        dst_service="shared-utils",
        src_container_kind="service",
        dst_container_kind="library",
        src_within="service",
        dst_within="library",
    )
    assert get_edge_field(e, "from.service") == "billing-service"
    assert get_edge_field(e, "to.service") == "shared-utils"
    assert get_edge_field(e, "from.kind") == "service"
    assert get_edge_field(e, "to.kind") == "library"
    assert get_edge_field(e, "from.within") == "service"
    assert get_edge_field(e, "to.within") == "library"


def test_get_edge_field_v2_within_for_nested_containers():
    """Test that 'within' differs from 'kind' for nested containers."""
    e = IREdge(
        src=cid("a"),
        dst=cid("b"),
        dep_type=DepType.IMPORT,
        src_service="shared-utils",
        dst_service="billing-service",
        src_container_kind="library",
        dst_container_kind="module",  # immediate container is a module
        src_within="library",
        dst_within="service",  # top-level container is a service
    )
    assert get_edge_field(e, "from.kind") == "library"
    assert get_edge_field(e, "from.within") == "library"
    assert get_edge_field(e, "to.kind") == "module"
    assert get_edge_field(e, "to.within") == "service"


def test_get_edge_field_v2_none_when_not_enriched():
    e = IREdge(src=cid("a"), dst=cid("b"), dep_type=DepType.IMPORT)
    assert get_edge_field(e, "from.service") is None
    assert get_edge_field(e, "to.service") is None
    assert get_edge_field(e, "from.kind") is None
    assert get_edge_field(e, "to.kind") is None
    assert get_edge_field(e, "from.within") is None
    assert get_edge_field(e, "to.within") is None
