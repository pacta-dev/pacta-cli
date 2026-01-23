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

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitVCSProvider:
    """
    Git-based VCS provider for extracting repository metadata.

    Provides:
      - Current commit SHA
      - Current branch name
      - Repository status information

    All operations are read-only and safe to run in any Git repository.
    """

    def current_commit(self, repo_root: str | Path) -> str | None:
        """
        Get the current commit SHA (HEAD).

        Args:
            repo_root: Path to repository root

        Returns:
            Commit SHA string, or None if not in a Git repository
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0:
                return result.stdout.strip()

            return None

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None

    def current_branch(self, repo_root: str | Path) -> str | None:
        """
        Get the current branch name.

        Args:
            repo_root: Path to repository root

        Returns:
            Branch name, or None if not in a Git repository or detached HEAD
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0:
                branch = result.stdout.strip()
                # "HEAD" means detached HEAD state
                if branch == "HEAD":
                    return None
                return branch

            return None

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return None

    def is_dirty(self, repo_root: str | Path) -> bool:
        """
        Check if the repository has uncommitted changes.

        Args:
            repo_root: Path to repository root

        Returns:
            True if there are uncommitted changes, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            if result.returncode == 0:
                # Non-empty output means there are changes
                return bool(result.stdout.strip())

            return False

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    def is_git_repo(self, repo_root: str | Path) -> bool:
        """
        Check if the path is inside a Git repository.

        Args:
            repo_root: Path to check

        Returns:
            True if inside a Git repository, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )

            return result.returncode == 0 and result.stdout.strip() == "true"

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
