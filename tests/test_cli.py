"""Tests for purgepilot.cli."""

from __future__ import annotations

import pytest
from pathlib import Path

from purgepilot.cli import main


@pytest.fixture()
def simple_tree(tmp_path: Path) -> Path:
    (tmp_path / "a" / "sub").mkdir(parents=True)
    (tmp_path / "b").mkdir()
    return tmp_path


class TestCLI:
    def test_basic_output(self, simple_tree: Path, capsys: pytest.CaptureFixture) -> None:
        main([str(simple_tree)])
        captured = capsys.readouterr()
        assert "a" in captured.out
        assert "b" in captured.out

    def test_max_depth_option(self, simple_tree: Path, capsys: pytest.CaptureFixture) -> None:
        main([str(simple_tree), "--max-depth", "0"])
        captured = capsys.readouterr()
        assert "sub" not in captured.out

    def test_nonexistent_path_exits(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path / "does_not_exist")])
        assert exc_info.value.code != 0

    def test_file_path_exits(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello")
        with pytest.raises(SystemExit) as exc_info:
            main([str(f)])
        assert exc_info.value.code != 0

    def test_empty_dir_message(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        main([str(tmp_path)])
        captured = capsys.readouterr()
        assert "No subdirectories found" in captured.out
