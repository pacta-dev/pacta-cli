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

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EngineConfig:
    repo_root: Path
    model_file: Path | None
    rules_files: tuple[Path, ...]
    baseline: str | None = None
    changed_only: bool = False
    include_paths: tuple[Path, ...] = ()
    exclude_globs: tuple[str, ...] = ()
    output_format: str = "text"
    deterministic: bool = True
    save_ref: str | None = None  # Save snapshot under this ref (in addition to "latest")
