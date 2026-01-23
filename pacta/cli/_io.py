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


def ensure_repo_root(path: str) -> str:
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")
    return str(p)


def default_rules_files(repo_root: str) -> tuple[str, ...]:
    p = Path(repo_root)
    candidate = p / "pacta.rules"
    return (str(candidate),) if candidate.exists() else ()


def default_model_file(repo_root: str) -> str | None:
    p = Path(repo_root)
    candidate = p / "architecture.yaml"
    return str(candidate) if candidate.exists() else None
