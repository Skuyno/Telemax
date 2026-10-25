"""Resolves the repository root this service operates on."""

from pathlib import Path

_FALLBACK_PARENTS_UP = 4


def resolve_repo_root(repo_root_env: str | None, main_file: Path) -> Path:
    """Resolve the repository root from REPO_ROOT, or infer it for dev use.

    Inside the real container only app/ is copied in (see Dockerfile), so
    the inferred fallback below would raise if it were ever evaluated there
    — it must only run when repo_root_env is actually absent, never as an
    eagerly-evaluated default (e.g. `os.environ.get(key, default)` computes
    `default` unconditionally, which would break this).

    Args:
        repo_root_env: the raw REPO_ROOT environment variable, or None.
        main_file: this service's own app/main.py path (`Path(__file__)`),
            used only to infer the repo root when REPO_ROOT isn't set.

    Returns:
        Path: the resolved repository root.
    """
    if repo_root_env:
        return Path(repo_root_env)
    return main_file.resolve().parents[_FALLBACK_PARENTS_UP]
