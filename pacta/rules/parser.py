from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from pacta.rules.ast import (
    AndAst,
    CompareAst,
    DependencyWhenAst,
    FieldAst,
    LiteralAst,
    NodeWhenAst,
    NotAst,
    OrAst,
    RuleAst,
    RulesDocumentAst,
    SourceSpan,
)
from pacta.rules.errors import RulesParseError

# Public protocol


class RulesParser(Protocol):
    """
    Parse a rules file (DSL/YAML/etc.) into a RulesDocumentAst.
    """

    def parse_text(self, text: str, *, filename: str | None = None) -> RulesDocumentAst:
        raise NotImplementedError()

    def parse_file(self, path: str | Path) -> RulesDocumentAst:
        raise NotImplementedError()


# Minimal DSL parser (v0)
#
# This is intentionally a very small parser that supports a compact YAML-like DSL
# without external dependencies. It is NOT meant to be a fully featured language yet.
#
# Supported format (v0):
#
# rule:
#   id: no-domain-to-infra
#   name: Domain must not depend on Infra
#   severity: error|warning|info
#   action: forbid|allow|require
#   target: dependency|node
#   when:
#     all:
#       - field: from.layer
#         op: ==
#         value: domain
#       - field: to.layer
#         op: ==
#         value: infra
#
# Multiple rules are separated by a blank line and repeated "rule:" blocks.
#


@dataclass(frozen=True, slots=True)
class DslRulesParserV0:
    """
    A minimal rules parser for a constrained YAML-ish DSL.

    Limitations:
    - indentation-sensitive
    - only supports: when/all, when/any, when/not
    - values are treated as strings unless list syntax [a,b,c] is used

    Intended only as a bootstrap parser.
    """

    def parse_file(self, path: str | Path) -> RulesDocumentAst:
        p = Path(path)
        return self.parse_text(p.read_text(encoding="utf-8"), filename=str(p))

    def parse_text(self, text: str, *, filename: str | None = None) -> RulesDocumentAst:
        filename = filename or "<rules>"

        parsed_rules = self._parse_rule_block(text,filename=filename)

        return RulesDocumentAst(rules=tuple(parsed_rules), span=SourceSpan(file=filename))

    def _parse_rule_block(self, block: str, *, filename: str) -> list[RuleAst]:
        try:
            import yaml
        except ImportError as e:
            raise RulesParseError(
                message="YAML rules require optional dependency PyYAML (pip install pyyaml).",
                file=filename,
            ) from e

        try:
            doc = yaml.safe_load(block)
        except Exception as e:
            raise RulesParseError(message=f"Invalid YAML in rule block: {e}", file=filename) from e

        if not isinstance(doc, Mapping) or doc.get("rules") is None:
            raise RulesParseError(message="Rule block must contain top-level 'rules:' list", file=filename)

        rules_list = doc["rules"]
        if not isinstance(rules_list, list):
            raise RulesParseError(message="'rules list' must be a list", file=filename)

        parsed_rules = []

        for root in rules_list:
            if not isinstance(root, Mapping):
                raise RulesParseError(message="'rule' must be a mapping", file=filename)
            rule_item = self._add_rule_in_list(root, filename = filename)
            parsed_rules.append(rule_item)

        return parsed_rules    



    def _add_rule_in_list(self, root: Mapping, *, filename:str) -> RuleAst:
        # Required fields
        rid = self._req_str(root, "id", filename)
        name = self._req_str(root, "name", filename)

        severity = self._opt_str(root, "severity", "error")
        action = self._opt_str(root, "action", "forbid")
        target = self._opt_str(root, "target", "dependency")

        message = self._opt_str(root, "message", None)
        suggestion = self._opt_str(root, "suggestion", None)
        description = self._opt_str(root, "description", None)

        when_obj = root.get("when")
        if when_obj is None:
            raise RulesParseError(message=f"Rule '{rid}' missing 'when:' block", file=filename)

        predicate = self._parse_when_predicate(when_obj, filename=filename)
        when_ast = (
            DependencyWhenAst(predicate=predicate) if target == "dependency" else NodeWhenAst(predicate=predicate)
        )

        return RuleAst(
            id=rid,
            name=name,
            description=description,
            severity=severity,
            action=action,
            when=when_ast,
            except_when=(),
            message=message,
            suggestion=suggestion,
            tags=(),
            span=SourceSpan(file=filename),
            metadata={"parser": "dsl-v0+pyyaml"},
        )

    def _split_rule_blocks(self, text: str) -> list[str]:
        lines = [ln.rstrip("\n") for ln in text.splitlines()]
        blocks: list[list[str]] = []
        current: list[str] = []

        def flush():
            nonlocal current
            if any(ln.strip() for ln in current):
                blocks.append(current)
            current = []

        for ln in lines:
            if not ln.strip():
                flush()
                continue
            current.append(ln)
        flush()

        filtered = []
        for b in blocks:
            first = next((ln for ln in b if ln.strip() and not ln.strip().startswith("#")), "")
            if first.strip() != "rules:":
                continue
            filtered.append("\n".join(b))
        return filtered

    def _parse_when_predicate(self, when_obj: Any, *, filename: str):
        if not isinstance(when_obj, Mapping):
            raise RulesParseError(message="'when' must be a mapping", file=filename)

        if "all" in when_obj:
            items = when_obj["all"]
            if not isinstance(items, list):
                raise RulesParseError(message="'when.all' must be a list", file=filename)
            return AndAst(items=tuple(self._parse_pred_item(x, filename=filename) for x in items))

        if "any" in when_obj:
            items = when_obj["any"]
            if not isinstance(items, list):
                raise RulesParseError(message="'when.any' must be a list", file=filename)
            return OrAst(items=tuple(self._parse_pred_item(x, filename=filename) for x in items))

        if "not" in when_obj:
            return NotAst(item=self._parse_pred_item(when_obj["not"], filename=filename))

        raise RulesParseError(message="when: must contain one of: all, any, not", file=filename)

    def _parse_pred_item(self, item: Any, *, filename: str):
        if isinstance(item, Mapping):
            if "all" in item or "any" in item or "not" in item:
                return self._parse_when_predicate(item, filename=filename)

            field = item.get("field")
            op = item.get("op", "==")
            value = item.get("value")

            if not isinstance(field, str) or not field.strip():
                raise RulesParseError(message="Predicate item missing non-empty 'field'", file=filename)
            if not isinstance(op, str) or not op.strip():
                raise RulesParseError(message="Predicate item missing non-empty 'op'", file=filename)

            lit = self._parse_literal(value)
            return CompareAst(left=FieldAst(path=field.strip()), op=op.strip(), right=lit)

        if isinstance(item, str):
            return self._parse_inline_compare(item, filename=filename)

        raise RulesParseError(message=f"Unsupported predicate item: {item!r}", file=filename)

    def _parse_inline_compare(self, text: str, *, filename: str):
        parts = text.strip().split()
        if len(parts) < 3:
            raise RulesParseError(message=f"Invalid inline predicate: {text!r}", file=filename)
        field, op = parts[0], parts[1]
        value = " ".join(parts[2:])
        return CompareAst(left=FieldAst(path=field), op=op, right=self._parse_literal(value))  # type: ignore[invalid-argument-type]

    def _parse_literal(self, value: Any) -> LiteralAst:
        if value is None:
            return LiteralAst(kind="null", value=None)
        if isinstance(value, bool):
            return LiteralAst(kind="bool", value=value)
        if isinstance(value, (int, float)):
            return LiteralAst(kind="number", value=value)
        if isinstance(value, list):
            return LiteralAst(kind="list", value=value)

        s = str(value).strip()
        if s.startswith("[") and s.endswith("]"):
            inner = s[1:-1].strip()
            if not inner:
                return LiteralAst(kind="list", value=[])
            parts = [p.strip() for p in inner.split(",")]
            return LiteralAst(kind="list", value=parts)

        return LiteralAst(kind="string", value=s)

    def _req_str(self, root: Mapping[str, Any], key: str, filename: str) -> str:
        if key not in root:
            raise RulesParseError(message=f"Missing required key: {key}", file=filename)
        val = root[key]
        if not isinstance(val, str) or not val.strip():
            raise RulesParseError(message=f"Key '{key}' must be a non-empty string", file=filename)
        return val.strip()

    def _opt_str(self, root: Mapping[str, Any], key: str, default):
        if key not in root:
            return default
        val = root[key]
        if val is None:
            return None
        return str(val).strip()
