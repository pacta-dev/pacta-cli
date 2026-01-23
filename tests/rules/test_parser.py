import pytest
from pacta.rules.ast import (
    AndAst,
    CompareAst,
    DependencyWhenAst,
    FieldAst,
    LiteralAst,
    NodeWhenAst,
    NotAst,
    OrAst,
    RulesDocumentAst,
)
from pacta.rules.errors import RulesParseError
from pacta.rules.parser import DslRulesParserV0

# Helpers


def parse(text: str):
    return DslRulesParserV0().parse_text(text, filename="rules.txt")


# Tests: block splitting


def test_parser_ignores_blocks_not_starting_with_rule():
    text = """
# comment block

something:
  not: a rule

rule:
  id: r1
  name: A
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    assert isinstance(doc, RulesDocumentAst)
    assert len(doc.rules) == 1
    assert doc.rules[0].id == "r1"


def test_parser_multiple_rule_blocks_separated_by_blank_lines():
    text = """
rule:
  id: r1
  name: First
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain

rule:
  id: r2
  name: Second
  target: dependency
  when:
    all:
      - field: from.layer
        op: ==
        value: domain
"""
    doc = parse(text)
    assert len(doc.rules) == 2
    assert doc.rules[0].id == "r1"
    assert doc.rules[1].id == "r2"


# Tests: when predicate parsing


def test_when_all_builds_and_ast_with_compare_items():
    text = """
rule:
  id: r1
  name: No domain -> infra
  target: dependency
  when:
    all:
      - field: from.layer
        op: ==
        value: domain
      - field: to.layer
        op: ==
        value: infra
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when, DependencyWhenAst)
    assert isinstance(r.when.predicate, AndAst)
    assert len(r.when.predicate.items) == 2

    c0 = r.when.predicate.items[0]
    assert isinstance(c0, CompareAst)
    assert isinstance(c0.left, FieldAst)
    assert c0.left.path == "from.layer"
    assert c0.op == "=="
    assert isinstance(c0.right, LiteralAst)
    assert c0.right.kind == "string"
    assert c0.right.value == "domain"


def test_when_any_builds_or_ast():
    text = """
rule:
  id: r1
  name: Any layer
  target: node
  when:
    any:
      - field: layer
        op: ==
        value: domain
      - field: layer
        op: ==
        value: infra
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when, NodeWhenAst)
    assert isinstance(r.when.predicate, OrAst)
    assert len(r.when.predicate.items) == 2


def test_when_not_builds_not_ast():
    text = """
rule:
  id: r1
  name: Not infra
  target: node
  when:
    not:
      field: layer
      op: ==
      value: infra
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when, NodeWhenAst)
    assert isinstance(r.when.predicate, NotAst)
    assert isinstance(r.when.predicate.item, CompareAst)
    assert r.when.predicate.item.left.path == "layer"


def test_inline_predicate_string_is_supported():
    text = """
rule:
  id: r1
  name: Inline
  target: dependency
  when:
    all:
      - from.layer == domain
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when, DependencyWhenAst)
    assert isinstance(r.when.predicate, AndAst)
    assert len(r.when.predicate.items) == 1
    c = r.when.predicate.items[0]
    assert isinstance(c, CompareAst)
    assert c.left.path == "from.layer"
    assert c.op == "=="
    assert c.right.value == "domain"


def test_list_literal_shorthand_is_parsed_into_list_literal():
    text = """
rule:
  id: r1
  name: In list
  target: node
  when:
    all:
      - field: kind
        op: in
        value: [module, package]
"""
    doc = parse(text)
    r = doc.rules[0]
    c = r.when.predicate.items[0]
    assert isinstance(c, CompareAst)
    assert isinstance(c.right, LiteralAst)
    assert c.right.kind == "list"
    assert c.right.value == ["module", "package"]


# Tests: rule metadata fields


def test_parser_reads_severity_action_message_suggestion_description():
    text = """
rule:
  id: r1
  name: Foo
  description: Hello
  severity: warning
  action: forbid
  target: node
  message: Bad node
  suggestion: Rename it
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    r = doc.rules[0]
    assert r.description == "Hello"
    assert r.severity == "warning"
    assert r.action == "forbid"
    assert r.message == "Bad node"
    assert r.suggestion == "Rename it"
    assert isinstance(r.metadata, dict)
    assert r.metadata.get("parser") == "dsl-v0+pyyaml"


# Tests: failures


def test_missing_when_is_parse_error():
    text = """
rule:
  id: r1
  name: Missing when
  target: node
"""
    with pytest.raises(RulesParseError) as ex:
        parse(text)

    msg = str(ex.value).lower()
    assert "missing" in msg
    assert "when" in msg


def test_when_missing_all_any_not_is_parse_error():
    text = """
rule:
  id: r1
  name: Bad when
  target: node
  when:
    x:
      - field: layer
        op: ==
        value: domain
"""
    with pytest.raises(RulesParseError) as ex:
        parse(text)
    assert "must contain" in str(ex.value).lower()


def test_invalid_indentation_raises_parse_error():
    text = """
rule:
  id: r1
  name: Bad indent
  target: node
  when:
    all:
      - field: layer
      op: ==
        value: domain
"""
    with pytest.raises(RulesParseError):
        parse(text)


def test_invalid_inline_predicate_is_parse_error():
    text = """
rule:
  id: r1
  name: Bad inline
  target: node
  when:
    all:
      - layer ==
"""
    with pytest.raises(RulesParseError):
        parse(text)


# Tests: comment handling


def test_parser_accepts_comments_before_rule_block():
    """Parser should skip comment lines when identifying rule blocks."""
    text = """
# This is a comment about the rule
# Another comment line
rule:
  id: r1
  name: Test Rule
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    assert len(doc.rules) == 1
    assert doc.rules[0].id == "r1"
    assert doc.rules[0].name == "Test Rule"


def test_parser_handles_inline_comments_in_rule_block():
    """Parser should ignore inline comments within rule blocks."""
    text = """
rule:
  id: r1
  name: Test
  # This is a comment inside the rule
  target: node
  # Another comment
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    assert len(doc.rules) == 1
    assert doc.rules[0].id == "r1"


def test_parser_handles_comments_between_rules():
    """Parser should handle comments between rule blocks."""
    text = """
rule:
  id: r1
  name: First
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain

# Comment between rules
# Another comment

rule:
  id: r2
  name: Second
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: infra
"""
    doc = parse(text)
    assert len(doc.rules) == 2
    assert doc.rules[0].id == "r1"
    assert doc.rules[1].id == "r2"


# Tests: YAML multiline string support


def test_parser_handles_yaml_pipe_multiline_strings():
    """Parser should handle YAML pipe (|) syntax for multiline strings."""
    text = """
rule:
  id: r1
  name: Test
  description: |
    This is a multiline description
    that spans multiple lines
    and should be preserved
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    r = doc.rules[0]
    assert r.description is not None
    assert "multiline description" in r.description
    assert "multiple lines" in r.description
    assert "\n" in r.description


def test_parser_handles_yaml_greater_than_multiline_strings():
    """Parser should handle YAML greater-than (>) syntax for multiline strings."""
    text = """
rule:
  id: r1
  name: Test
  message: >
    This is a folded
    multiline message
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    r = doc.rules[0]
    assert r.message is not None
    assert "folded" in r.message
    assert "multiline message" in r.message


def test_parser_handles_multiline_in_multiple_fields():
    """Parser should handle multiline strings in description, message, and suggestion."""
    text = """
rule:
  id: r1
  name: Test
  description: |
    Multiline description
    with details
  message: |
    Multiline message
    explaining the violation
  suggestion: |
    Multiline suggestion
    for fixing the issue
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain
"""
    doc = parse(text)
    r = doc.rules[0]
    assert "Multiline description" in r.description
    assert "Multiline message" in r.message
    assert "Multiline suggestion" in r.suggestion


# Tests: nested predicate support


def test_parser_handles_nested_any_in_all():
    """Parser should handle nested 'any' blocks inside 'all' blocks."""
    text = """
rule:
  id: r1
  name: Nested predicates
  target: dependency
  when:
    all:
      - field: from.layer
        op: ==
        value: application
      - any:
          - field: to.layer
            op: ==
            value: domain
          - field: to.layer
            op: ==
            value: infra
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when.predicate, AndAst)
    assert len(r.when.predicate.items) == 2

    # First item should be a compare
    first = r.when.predicate.items[0]
    assert isinstance(first, CompareAst)
    assert first.left.path == "from.layer"

    # Second item should be an OrAst
    second = r.when.predicate.items[1]
    assert isinstance(second, OrAst)
    assert len(second.items) == 2


def test_parser_handles_nested_all_in_any():
    """Parser should handle nested 'all' blocks inside 'any' blocks."""
    text = """
rule:
  id: r1
  name: Nested predicates
  target: dependency
  when:
    any:
      - all:
          - field: from.layer
            op: ==
            value: domain
          - field: to.layer
            op: ==
            value: infra
      - field: from.layer
        op: ==
        value: ui
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when.predicate, OrAst)
    assert len(r.when.predicate.items) == 2

    # First item should be an AndAst
    first = r.when.predicate.items[0]
    assert isinstance(first, AndAst)
    assert len(first.items) == 2


def test_parser_handles_nested_not_in_all():
    """Parser should handle nested 'not' blocks inside 'all' blocks."""
    text = """
rule:
  id: r1
  name: Nested not
  target: node
  when:
    all:
      - field: layer
        op: ==
        value: domain
      - not:
          field: kind
          op: ==
          value: test
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when.predicate, AndAst)
    assert len(r.when.predicate.items) == 2

    # Second item should be a NotAst
    second = r.when.predicate.items[1]
    assert isinstance(second, NotAst)
    assert isinstance(second.item, CompareAst)


def test_parser_handles_deeply_nested_predicates():
    """Parser should handle multiple levels of nesting."""
    text = """
rule:
  id: r1
  name: Deeply nested
  target: dependency
  when:
    all:
      - field: from.layer
        op: ==
        value: application
      - any:
          - all:
              - field: to.layer
                op: ==
                value: domain
              - field: to.kind
                op: ==
                value: class
          - field: to.layer
            op: ==
            value: infra
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when.predicate, AndAst)

    # Top level has 2 items
    assert len(r.when.predicate.items) == 2

    # Second item is an OrAst
    or_ast = r.when.predicate.items[1]
    assert isinstance(or_ast, OrAst)
    assert len(or_ast.items) == 2

    # First item in OrAst is an AndAst
    nested_and = or_ast.items[0]
    assert isinstance(nested_and, AndAst)
    assert len(nested_and.items) == 2


def test_parser_handles_inline_predicates_with_nesting():
    """Parser should handle inline predicate syntax within nested structures."""
    text = """
rule:
  id: r1
  name: Inline with nesting
  target: dependency
  when:
    all:
      - from.layer == application
      - any:
          - to.layer == domain
          - to.layer == infra
"""
    doc = parse(text)
    r = doc.rules[0]
    assert isinstance(r.when.predicate, AndAst)
    assert len(r.when.predicate.items) == 2

    # First item uses inline syntax
    first = r.when.predicate.items[0]
    assert isinstance(first, CompareAst)
    assert first.left.path == "from.layer"
    assert first.right.value == "application"

    # Second item is nested any with inline syntax
    second = r.when.predicate.items[1]
    assert isinstance(second, OrAst)
    assert len(second.items) == 2
    assert all(isinstance(item, CompareAst) for item in second.items)
