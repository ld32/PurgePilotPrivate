"""Tests for purgepilot.scanner."""

from __future__ import annotations

import pytest
from pathlib import Path

from purgepilot.scanner import FolderInfo, scan_folders


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def simple_tree(tmp_path: Path) -> Path:
    """Create a simple directory tree for testing.

    tmp_path/
        a/
            a1/
            a2/
        b/
        .hidden/
    """
    (tmp_path / "a" / "a1").mkdir(parents=True)
    (tmp_path / "a" / "a2").mkdir(parents=True)
    (tmp_path / "b").mkdir()
    (tmp_path / ".hidden").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Basic scanning
# ---------------------------------------------------------------------------

class TestScanFolders:
    def test_returns_list_of_folder_info(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree)
        assert isinstance(result, list)
        assert all(isinstance(f, FolderInfo) for f in result)

    def test_finds_all_non_hidden_dirs(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree)
        names = {f.name for f in result}
        assert names == {"a", "a1", "a2", "b"}

    def test_hidden_dirs_excluded_by_default(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree)
        names = {f.name for f in result}
        assert ".hidden" not in names

    def test_hidden_dirs_included_when_requested(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree, include_hidden=True)
        names = {f.name for f in result}
        assert ".hidden" in names

    def test_depth_values(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree)
        by_name = {f.name: f for f in result}
        assert by_name["a"].depth == 0
        assert by_name["b"].depth == 0
        assert by_name["a1"].depth == 1
        assert by_name["a2"].depth == 1

    def test_max_depth_zero(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree, max_depth=0)
        names = {f.name for f in result}
        assert names == {"a", "b"}
        assert "a1" not in names

    def test_max_depth_one(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree, max_depth=1)
        names = {f.name for f in result}
        assert {"a", "b", "a1", "a2"} == names

    def test_empty_directory(self, tmp_path: Path) -> None:
        result = scan_folders(tmp_path)
        assert result == []

    def test_raises_for_non_directory(self, tmp_path: Path) -> None:
        file_path = tmp_path / "file.txt"
        file_path.write_text("hello")
        with pytest.raises(NotADirectoryError):
            scan_folders(file_path)

    def test_root_itself_not_included(self, simple_tree: Path) -> None:
        result = scan_folders(simple_tree)
        paths = {f.path for f in result}
        assert simple_tree not in paths

    def test_string_path_accepted(self, simple_tree: Path) -> None:
        result = scan_folders(str(simple_tree))
        assert len(result) > 0
