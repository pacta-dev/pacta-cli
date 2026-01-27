"""
Content-addressed snapshot store with git-like refs.

Storage layout:
  .pacta/snapshots/
  ├── objects/
  │   ├── a1b2c3d4.json     # Content-addressed (8-char hash prefix)
  │   ├── e5f6g7h8.json
  │   └── ...
  └── refs/
      ├── latest            # Text file containing hash: a1b2c3d4
      ├── baseline          # Text file containing hash: e5f6g7h8
      └── ...

Every save creates a new object file (hash of content).
Refs are aliases pointing to object hashes.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pacta.snapshot.jsonutil import dumps_deterministic, load_file
from pacta.snapshot.types import Snapshot, SnapshotRef

# Length of hash prefix used for object filenames
HASH_PREFIX_LENGTH = 8


@dataclass(frozen=True)
class SaveResult:
    """Result of saving a snapshot."""

    object_hash: str  # Full SHA256 hash
    short_hash: str  # 8-char prefix used as filename
    object_path: Path  # Path to the object file
    refs_updated: tuple[str, ...]  # Refs that were created/updated


class FsSnapshotStore:
    """
    Content-addressed snapshot store with git-like refs.

    Snapshots are stored by content hash (immutable objects).
    Refs are mutable pointers to object hashes.
    """

    def __init__(self, repo_root: str, *, base_dir: str = ".pacta/snapshots") -> None:
        self._repo_root = Path(repo_root)
        self._base_dir = self._repo_root / base_dir
        self._objects_dir = self._base_dir / "objects"
        self._refs_dir = self._base_dir / "refs"

    def _compute_hash(self, snapshot: Snapshot) -> str:
        """Compute SHA256 hash of snapshot content."""
        content = dumps_deterministic(snapshot.to_dict())
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _object_path(self, short_hash: str) -> Path:
        """Get path to object file by short hash."""
        return self._objects_dir / f"{short_hash}.json"

    def save(
        self,
        snapshot: Snapshot,
        *,
        refs: tuple[str, ...] | list[str] | None = None,
    ) -> SaveResult:
        """
        Save snapshot as content-addressed object.

        Args:
            snapshot: The snapshot to save
            refs: Optional ref names to point to this snapshot

        Returns:
            SaveResult with hash and paths
        """
        # Compute content hash
        full_hash = self._compute_hash(snapshot)
        short_hash = full_hash[:HASH_PREFIX_LENGTH]

        # Save object file
        object_path = self._object_path(short_hash)
        object_path.parent.mkdir(parents=True, exist_ok=True)

        # Include hash in the saved data for verification
        data = snapshot.to_dict()
        data["_hash"] = full_hash

        object_path.write_text(
            json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        # Update refs if specified
        refs_updated: list[str] = []
        if refs:
            for ref_name in refs:
                self._update_ref(ref_name, short_hash)
                refs_updated.append(ref_name)

        return SaveResult(
            object_hash=full_hash,
            short_hash=short_hash,
            object_path=object_path,
            refs_updated=tuple(refs_updated),
        )

    def update_object(self, short_hash: str, snapshot: Snapshot) -> None:
        """
        Overwrite an existing object file in-place.

        This is used by `pacta check` to write violations back into
        an existing snapshot without creating a new object.
        """
        path = self._object_path(short_hash)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot object not found: {short_hash}")

        data = snapshot.to_dict()
        # Preserve the original hash as the identifier
        data["_hash"] = short_hash

        path.write_text(
            json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def load_object(self, short_hash: str) -> Snapshot:
        """Load snapshot by short hash."""
        path = self._object_path(short_hash)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot object not found: {short_hash}")
        data = load_file(path)
        # Remove internal hash before parsing
        data.pop("_hash", None)
        return Snapshot.from_dict(data)

    def object_exists(self, short_hash: str) -> bool:
        """Check if object exists by short hash."""
        return self._object_path(short_hash).exists()

    def list_objects(self) -> list[tuple[str, Snapshot]]:
        """
        List all objects sorted by created_at timestamp (newest first).

        Returns:
            List of (short_hash, snapshot) tuples
        """
        if not self._objects_dir.exists():
            return []

        objects: list[tuple[str, Snapshot]] = []
        for path in self._objects_dir.glob("*.json"):
            short_hash = path.stem
            try:
                snapshot = self.load_object(short_hash)
                objects.append((short_hash, snapshot))
            except Exception:
                # Skip corrupted files
                continue

        # Sort by created_at (newest first)
        objects.sort(
            key=lambda x: x[1].meta.created_at or "",
            reverse=True,
        )
        return objects

    def _ref_path(self, ref_name: str) -> Path:
        """Get path to ref file."""
        return self._refs_dir / ref_name

    def _update_ref(self, ref_name: str, short_hash: str) -> None:
        """Create or update a ref to point to a hash."""
        ref_path = self._ref_path(ref_name)
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(short_hash + "\n", encoding="utf-8")

    def resolve_ref(self, ref_name: str) -> str | None:
        """Resolve a ref name to its target hash."""
        ref_path = self._ref_path(ref_name)
        if not ref_path.exists():
            return None
        return ref_path.read_text(encoding="utf-8").strip()

    def ref_exists(self, ref_name: str) -> bool:
        """Check if a ref exists."""
        return self._ref_path(ref_name).exists()

    def list_refs(self) -> dict[str, str]:
        """
        List all refs and their target hashes.

        Returns:
            Dict mapping ref_name -> short_hash
        """
        if not self._refs_dir.exists():
            return {}

        refs: dict[str, str] = {}
        for path in self._refs_dir.iterdir():
            if path.is_file():
                refs[path.name] = path.read_text(encoding="utf-8").strip()
        return refs

    def delete_ref(self, ref_name: str) -> bool:
        """Delete a ref. Returns True if deleted, False if didn't exist."""
        ref_path = self._ref_path(ref_name)
        if ref_path.exists():
            ref_path.unlink()
            return True
        return False

    def load(self, ref_or_hash: SnapshotRef) -> Snapshot:
        """
        Load snapshot by ref name or hash.

        Resolution order:
        1. If it looks like a hash (8+ hex chars), try as object
        2. Try as ref name
        3. Raise FileNotFoundError
        """
        # Try as ref first
        resolved_hash = self.resolve_ref(ref_or_hash)
        if resolved_hash:
            return self.load_object(resolved_hash)

        # Try as direct hash
        if self._looks_like_hash(ref_or_hash) and self.object_exists(ref_or_hash):
            return self.load_object(ref_or_hash)

        raise FileNotFoundError(f"Snapshot not found: {ref_or_hash}")

    def exists(self, ref_or_hash: SnapshotRef) -> bool:
        """Check if snapshot exists by ref name or hash."""
        # Check as ref
        if self.ref_exists(ref_or_hash):
            return True
        # Check as hash
        if self._looks_like_hash(ref_or_hash):
            return self.object_exists(ref_or_hash)
        return False

    def _looks_like_hash(self, s: str) -> bool:
        """Check if string looks like a hash (8+ hex chars)."""
        if len(s) < HASH_PREFIX_LENGTH:
            return False
        try:
            int(s[:HASH_PREFIX_LENGTH], 16)
            return True
        except ValueError:
            return False

    def resolve_path(self, ref: SnapshotRef) -> Path:
        """
        DEPRECATED: For backward compatibility only.

        New code should use load() and save() directly.
        """
        # If it's a ref, resolve to object path
        resolved = self.resolve_ref(ref)
        if resolved:
            return self._object_path(resolved)
        # If it looks like a hash, return object path
        if self._looks_like_hash(ref):
            return self._object_path(ref)
        # Legacy behavior: treat as direct path
        p = Path(ref)
        if p.suffix == ".json" or "/" in ref or "\\" in ref:
            return p if p.is_absolute() else (self._repo_root / p)
        # Default: treat as ref that doesn't exist yet
        return self._object_path(ref)
