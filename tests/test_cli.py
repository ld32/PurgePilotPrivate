"""Additional CLI tests for purge_pilot.main."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from purge_pilot.llm_client import PurgeReport
from purge_pilot.main import main


def test_main_uses_environment_defaults(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PURGE_PILOT_API_URL", "http://env-server/v1")
    monkeypatch.setenv("PURGE_PILOT_MODEL", "env-model")
    monkeypatch.setenv("PURGE_PILOT_API_KEY", "env-key")

    report = PurgeReport(root=str(tmp_path), estimates=[])

    with (
        patch("purge_pilot.main.scan_directory") as mock_scan,
        patch("purge_pilot.main.estimate_purge_confidence", return_value=report) as mock_estimate,
    ):
        mock_scan.return_value = MagicMock(entries=[], total_size_bytes=0)
        rc = main([str(tmp_path)])

    assert rc == 0
    _, kwargs = mock_estimate.call_args
    assert kwargs["api_url"] == "http://env-server/v1"
    assert kwargs["model"] == "env-model"
    assert kwargs["api_key"] == "env-key"
    assert "(no estimates returned by LLM)" in capsys.readouterr().out


def test_main_processes_multiple_directories_independently(tmp_path, capsys):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    scan_results = [
        MagicMock(entries=[], total_size_bytes=0),
        MagicMock(entries=[], total_size_bytes=0),
    ]
    reports = [
        PurgeReport(root=str(first), estimates=[]),
        PurgeReport(root=str(second), estimates=[]),
    ]

    with (
        patch("purge_pilot.main.scan_directory", side_effect=scan_results) as mock_scan,
        patch("purge_pilot.main.estimate_purge_confidence", side_effect=reports),
    ):
        rc = main([str(first), str(second), "--api-url", "http://x/v1", "--model", "m"])

    assert rc == 0
    assert mock_scan.call_count == 2
    output = capsys.readouterr().out
    assert str(first) in output
    assert str(second) in output
