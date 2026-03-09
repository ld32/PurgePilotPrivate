"""Scanner module – scan a directory tree and return folder information."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class FolderInfo:
    """Metadata for a single scanned folder."""

    path: Path
    name: str
    depth: int
    parent: Optional[Path]
    def __repr__(self) -> str:  # pragma: no cover
        return f"FolderInfo(path={self.path!r}, depth={self.depth})"


def scan_folders(
    root: str | os.PathLike,
    *,
    max_depth: Optional[int] = None,
    include_hidden: bool = False,
) -> List[FolderInfo]:
    """Recursively scan *root* and return a flat list of :class:`FolderInfo` objects.

    Parameters
    ----------
    root:
        The directory to scan.
    max_depth:
        Maximum recursion depth.  ``None`` means unlimited.
        Depth 0 means only the immediate children of *root*.
    include_hidden:
        When ``False`` (default) directories whose names start with ``.``
        are skipped.

    Returns
    -------
    list[FolderInfo]
        Flat list of all subdirectories found, ordered by depth then
        alphabetically by path.  The *root* itself is **not** included.

    Raises
    ------
    NotADirectoryError
        If *root* does not point to a directory.
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise NotADirectoryError(f"{root_path!r} is not a directory")

    results: List[FolderInfo] = []
    _walk(root_path, root_path, depth=0, max_depth=max_depth,
          include_hidden=include_hidden, results=results)
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _walk(
    root_path: Path,
    current: Path,
    *,
    depth: int,
    max_depth: Optional[int],
    include_hidden: bool,
    results: List[FolderInfo],
) -> None:
    """Recursive DFS walker."""
    if max_depth is not None and depth > max_depth:
        return

    try:
        entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        return

    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            continue
        if not include_hidden and entry.name.startswith("."):
            continue

        parent = entry.parent if entry.parent != root_path else None
        info = FolderInfo(
            path=entry,
            name=entry.name,
            depth=depth,
            parent=parent,
        )
        results.append(info)
        _walk(root_path, entry, depth=depth + 1, max_depth=max_depth,
              include_hidden=include_hidden, results=results)
