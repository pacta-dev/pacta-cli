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

# Core types (stable public API)

# Indexing & querying
from pacta.ir.index import (
    IRIndex,
    build_index,
)

# Identity / keys
from pacta.ir.keys import (
    dedupe_edges,
    dedupe_nodes,
    edge_key,
    node_key,
)

# IR processing
from pacta.ir.merge import DefaultIRMerger
from pacta.ir.normalize import DefaultIRNormalizer
from pacta.ir.select import (
    EdgeFilter,
    NodeFilter,
    match_glob,
    match_regex,
    select_edges,
    select_nodes,
)
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

# Validation
from pacta.ir.validate import (
    IRValidationOptions,
    validate_ir,
)

# Public export control

__all__ = (
    # types
    "ArchitectureIR",
    "IRNode",
    "IREdge",
    "CanonicalId",
    "SourceLoc",
    "SourcePos",
    "Language",
    "SymbolKind",
    "DepType",
    # keys
    "node_key",
    "edge_key",
    "dedupe_nodes",
    "dedupe_edges",
    # processing
    "DefaultIRMerger",
    "DefaultIRNormalizer",
    # indexing
    "IRIndex",
    "build_index",
    # selection
    "NodeFilter",
    "EdgeFilter",
    "select_nodes",
    "select_edges",
    "match_glob",
    "match_regex",
    # validation
    "validate_ir",
    "IRValidationOptions",
)
