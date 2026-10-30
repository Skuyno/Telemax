"""Tests for the deploy/.installed marker."""

import json
from pathlib import Path

from app.marker import is_installed, read_installed_marker, write_installed_marker


def test_is_installed_false_when_no_marker(tmp_path: Path) -> None:
    """A fresh repo with no marker file is not installed."""
    assert is_installed(tmp_path) is False


def test_write_then_is_installed_true(tmp_path: Path) -> None:
    """Writing the marker is immediately reflected by is_installed."""
    (tmp_path / "deploy").mkdir()

    write_installed_marker(tmp_path, version="0.1.0")

    assert is_installed(tmp_path) is True


def test_write_installed_marker_records_version_and_timestamp(tmp_path: Path) -> None:
    """The marker file carries the version and an ISO timestamp."""
    (tmp_path / "deploy").mkdir()

    write_installed_marker(tmp_path, version="0.2.0")

    marker_file = tmp_path / "deploy" / ".installed"
    payload = json.loads(marker_file.read_text(encoding="utf-8"))
    assert payload["version"] == "0.2.0"
    assert "installed_at" in payload


def test_read_installed_marker_returns_none_when_absent(tmp_path: Path) -> None:
    """No marker file reads back as None, not an error."""
    assert read_installed_marker(tmp_path) is None


def test_read_installed_marker_returns_parsed_payload(tmp_path: Path) -> None:
    """A written marker reads back with the same fields."""
    (tmp_path / "deploy").mkdir()
    write_installed_marker(tmp_path, version="0.3.0")

    payload = read_installed_marker(tmp_path)

    assert payload is not None
    assert payload["version"] == "0.3.0"
