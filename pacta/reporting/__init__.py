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

from pacta.reporting.builder import DefaultReportBuilder
from pacta.reporting.keys import DefaultViolationKeyFactory
from pacta.reporting.renderers.json import JsonReportRenderer
from pacta.reporting.renderers.text import TextReportRenderer
from pacta.reporting.types import (
    DiffSummary,
    EngineError,
    EngineErrorType,
    Report,
    ReportLocation,
    RuleRef,
    RunInfo,
    Severity,
    Summary,
    Violation,
    ViolationStatus,
)

__all__ = [
    "Severity",
    "ReportLocation",
    "EngineError",
    "EngineErrorType",
    "RuleRef",
    "Violation",
    "ViolationStatus",
    "RunInfo",
    "Summary",
    "DiffSummary",
    "Report",
    "DefaultReportBuilder",
    "DefaultViolationKeyFactory",
    "JsonReportRenderer",
    "TextReportRenderer",
]
