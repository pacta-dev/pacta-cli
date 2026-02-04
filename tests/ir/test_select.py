from pacta.ir.select import (
    match_any_glob,
    match_glob,
    match_regex,
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
