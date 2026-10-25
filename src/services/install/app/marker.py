"""Reads/writes the deploy/.installed marker that gates re-installation."""

import json
from datetime import UTC, datetime
from pathlib import Path


def marker_path(repo_root: Path) -> Path:
    """Path to the install marker file.

    Args:
        repo_root: absolute path to the repository root.

    Returns:
        Path: `<repo_root>/deploy/.installed`.
    """
    return repo_root / "deploy" / ".installed"


def is_installed(repo_root: Path) -> bool:
    """Whether a previous run already completed successfully.

    Args:
        repo_root: absolute path to the repository root.

    Returns:
        bool: True if the marker file exists.
    """
    return marker_path(repo_root).exists()


def write_installed_marker(repo_root: Path, version: str) -> None:
    """Record a successful installation, gating any future re-run.

    Args:
        repo_root: absolute path to the repository root.
        version: the app version string (from the repo's VERSION file).
    """
    payload = {"version": version, "installed_at": datetime.now(UTC).isoformat()}
    marker_path(repo_root).write_text(json.dumps(payload), encoding="utf-8")


def read_installed_marker(repo_root: Path) -> dict | None:
    """Read the marker's contents, if present.

    Args:
        repo_root: absolute path to the repository root.

    Returns:
        dict | None: the parsed marker payload, or None if not installed.
    """
    path = marker_path(repo_root)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
