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

from pacta.snapshot.jsonutil import dump_file, load_file
from pacta.snapshot.types import Snapshot, SnapshotRef


class FsSnapshotStore:
    """
    Stores snapshots as deterministic JSON on disk.

    Default layout:
      <repo_root>/.pacta/snapshots/<ref>.json

    If ref ends with ".json" (or contains a path separator), it is treated as a direct path.
    """

    def __init__(self, repo_root: str, *, base_dir: str = ".pacta/snapshots") -> None:
        self._repo_root = Path(repo_root)
        self._base_dir = self._repo_root / base_dir

    def resolve_path(self, ref: SnapshotRef) -> Path:
        p = Path(ref)
        if p.suffix == ".json" or "/" in ref or "\\" in ref:
            # treat as explicit path (absolute or relative)
            return p if p.is_absolute() else (self._repo_root / p)
        return self._base_dir / f"{ref}.json"

    def exists(self, ref: SnapshotRef) -> bool:
        return self.resolve_path(ref).exists()

    def save(self, snapshot: Snapshot, ref: SnapshotRef) -> Path:
        path = self.resolve_path(ref)
        dump_file(path, snapshot.to_dict())
        return path

    def load(self, ref: SnapshotRef) -> Snapshot:
        path = self.resolve_path(ref)
        data = load_file(path)
        return Snapshot.from_dict(data)  # relies on your Snapshot.to_dict format
