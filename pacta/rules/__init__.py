# SPDX-License-Identifier: AGPL-3.0-only
#
# Copyright (c) 2026 Pacta Contributors
#
# This file is part of Pacta.
#
# Pacta is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3 only.
#
# Pacta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.

from pathlib import Path

from pacta.rules.ast import (
    AndAst,
    CompareAst,
    DependencyWhenAst,
    ExprAst,
    FieldAst,
    LiteralAst,
    NodeWhenAst,
    NotAst,
    OrAst,
    RuleAst,
    RulesDocumentAst,
    WhenAst,
)
from pacta.rules.baseline import BaselineComparer, BaselineResult, ViolationKeyStrategy
from pacta.rules.compiler import RulesCompiler
from pacta.rules.dsl import DefaultDSLParser
from pacta.rules.errors import RulesCompileError, RulesError, RulesEvalError, RulesParseError
from pacta.rules.evaluator import DefaultRuleEvaluator, RuleEvaluatorProtocol
from pacta.rules.explain import explain_rule, explain_violation
from pacta.rules.loader import DefaultRuleSourceLoader, RuleSource
from pacta.rules.parser import DslRulesParserV0, RulesParser
from pacta.rules.types import Rule, RuleAction, RuleSet, RuleTarget

__all__ = [
    # AST
    "RulesDocumentAst",
    "RuleAst",
    "WhenAst",
    "DependencyWhenAst",
    "NodeWhenAst",
    "ExprAst",
    "AndAst",
    "OrAst",
    "NotAst",
    "CompareAst",
    "FieldAst",
    "LiteralAst",
    # Runtime types
    "Rule",
    "RuleAction",
    "RuleTarget",
    "RuleSet",
    # Parsing / compiling
    "RulesParser",
    "DslRulesParserV0",
    "DefaultDSLParser",
    "RulesCompiler",
    # Loading
    "DefaultRuleSourceLoader",
    "RuleSource",
    # Evaluation
    "RuleEvaluatorProtocol",
    "DefaultRuleEvaluator",
    # Baseline
    "ViolationKeyStrategy",
    "BaselineComparer",
    "BaselineResult",
    # Explain
    "explain_rule",
    "explain_violation",
    # Errors
    "RulesError",
    "RulesParseError",
    "RulesCompileError",
    "RulesEvalError",
]

# Convenience helpers (public API)


def load_rules(path: str | Path):
    """
    Load and compile rules from a file.

    Currently uses the v0 DSL parser.
    """
    parser = DslRulesParserV0()
    compiler = RulesCompiler()

    doc = parser.parse_file(path)
    return compiler.compile(doc)


def evaluate(ir, rules: RuleSet):
    """
    Evaluate compiled rules against IR or IRIndex.
    """
    evaluator = DefaultRuleEvaluator()
    return evaluator.evaluate(ir, rules)
