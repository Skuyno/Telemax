"""Tests for REPO_ROOT resolution.

Exists specifically because of a real bug caught by an actual container run:
`os.environ.get("REPO_ROOT", <fallback expression>)` evaluates the fallback
eagerly, even when REPO_ROOT is set — and inside the real container, that
fallback (only app/ is copied in, no full repo tree) raises IndexError on
every single startup, regardless of REPO_ROOT. resolve_repo_root must only
ever touch main_file when repo_root_env is falsy.
"""

from pathlib import Path

from app.repo_root import resolve_repo_root


def test_uses_the_env_value_when_present() -> None:
    """REPO_ROOT, when set, wins outright — no filesystem inspection at all."""
    result = resolve_repo_root("/repo", main_file=Path("/does/not/exist/main.py"))

    assert result == Path("/repo")


def test_falls_back_to_inferring_from_main_file_when_env_is_none() -> None:
    """With no REPO_ROOT, the repo root is inferred from this file's own path."""
    main_file = Path(__file__).resolve().parents[1] / "app" / "main.py"

    result = resolve_repo_root(None, main_file=main_file)

    assert result == Path(__file__).resolve().parents[4]


def test_falls_back_when_env_is_an_empty_string() -> None:
    """An empty REPO_ROOT is treated the same as unset, not as a literal path."""
    main_file = Path(__file__).resolve().parents[1] / "app" / "main.py"

    result = resolve_repo_root("", main_file=main_file)

    assert result != Path("")
