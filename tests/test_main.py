"""Tests for purge_pilot.main (CLI)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from purge_pilot.llm_client import PurgeEstimate, PurgeReport
from purge_pilot.main import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_report(root: str, estimates=None) -> PurgeReport:
    if estimates is None:
        estimates = [
            PurgeEstimate(path="old.tar.gz", confidence=0.95, reason="Old archive"),
            PurgeEstimate(path="data.csv", confidence=0.1, reason="Active dataset"),
        ]
    return PurgeReport(root=root, estimates=estimates)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_main_text_output(tmp_path, capsys):
    report = _mock_report(str(tmp_path))
    with (
        patch("purge_pilot.main.scan_directory") as mock_scan,
        patch("purge_pilot.main.estimate_purge_confidence", return_value=report),
    ):
        mock_scan.return_value = MagicMock(entries=[], total_size_bytes=0)
        rc = main([str(tmp_path), "--api-url", "http://localhost:11434/v1", "--model", "llama3"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "old.tar.gz" in out
    assert "0.95" in out
    assert "Old archive" in out


def test_main_json_output(tmp_path, capsys):
    report = _mock_report(str(tmp_path))
    with (
        patch("purge_pilot.main.scan_directory") as mock_scan,
        patch("purge_pilot.main.estimate_purge_confidence", return_value=report),
    ):
        mock_scan.return_value = MagicMock(entries=[], total_size_bytes=0)
        rc = main([str(tmp_path), "--output", "json", "--api-url", "http://x/v1", "--model", "m"])

    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["root"] == str(tmp_path)
    assert len(data["estimates"]) == 2


def test_main_nonexistent_directory(tmp_path, capsys):
    rc = main([str(tmp_path / "does_not_exist")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err.lower()


def test_main_path_is_file_not_dir(tmp_path, capsys):
    f = tmp_path / "file.txt"
    f.write_text("x")
    rc = main([str(f)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "not a directory" in err.lower()


def test_main_llm_error_returns_nonzero(tmp_path, capsys):
    with (
        patch("purge_pilot.main.scan_directory") as mock_scan,
        patch(
            "purge_pilot.main.estimate_purge_confidence",
            side_effect=RuntimeError("connection refused"),
        ),
    ):
        mock_scan.return_value = MagicMock(entries=[], total_size_bytes=0)
        rc = main([str(tmp_path), "--api-url", "http://bad/v1", "--model", "x"])

    assert rc == 1
    err = capsys.readouterr().err
    assert "connection refused" in err.lower()


def test_main_scan_passes_max_depth(tmp_path):
    report = _mock_report(str(tmp_path), estimates=[])
    with (
        patch("purge_pilot.main.scan_directory") as mock_scan,
        patch("purge_pilot.main.estimate_purge_confidence", return_value=report),
    ):
        mock_scan.return_value = MagicMock(entries=[], total_size_bytes=0)
        main([str(tmp_path), "--max-depth", "3", "--api-url", "http://x/v1", "--model", "m"])

    _, kwargs = mock_scan.call_args
    assert kwargs["max_depth"] == 3


def test_main_scan_passes_include_hidden(tmp_path):
    report = _mock_report(str(tmp_path), estimates=[])
    with (
        patch("purge_pilot.main.scan_directory") as mock_scan,
        patch("purge_pilot.main.estimate_purge_confidence", return_value=report),
    ):
        mock_scan.return_value = MagicMock(entries=[], total_size_bytes=0)
        main([str(tmp_path), "--include-hidden", "--api-url", "http://x/v1", "--model", "m"])

    _, kwargs = mock_scan.call_args
    assert kwargs["include_hidden"] is True
