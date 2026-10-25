"""Validates the actual install.yml files committed to this repo.

Unlike test_discovery.py (which only exercises discover_manifests against
synthetic tmp_path fixtures), this runs against the real repository tree —
catching a manifest broken by some future change before it ever reaches a
live install, cheaply (no Docker, no Postgres, no network) in CI.
"""

from pathlib import Path

from app.discovery import (
    collect_secret_refs,
    discover_manifests,
    load_shared_secrets,
    resolve_secret_spec,
)

# tests/test_real_manifests.py -> tests -> install -> services -> src -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHARED_SECRETS_PATH = Path(__file__).resolve().parents[1] / "shared_secrets.yml"

# The services known to ship their own install.yml as of this writing (plus
# deploy/ itself) — a real regression (e.g. a service's install.yml going
# missing) should fail this, not silently shrink the discovered set.
_EXPECTED_MANIFEST_DIRS = {
    "deploy",
    "identity",
    "communication",
    "file-orchestrator",
    "api-gateway",
    "ws-gateway",
}


def test_every_real_install_yml_parses_without_error() -> None:
    """Every install.yml actually committed to the repo must validate.

    discover_manifests raises ManifestError on the first invalid file it
    finds, naming the file — so simply calling it without an exception is
    the actual assertion here.
    """
    manifests = discover_manifests(_REPO_ROOT)

    found_dirs = {m.service_dir.name for m in manifests}
    assert _EXPECTED_MANIFEST_DIRS <= found_dirs


def test_real_shared_secrets_yml_parses() -> None:
    """The real shared_secrets.yml registry validates and has the expected entries."""
    secrets = load_shared_secrets(_SHARED_SECRETS_PATH)

    assert "postgres_password" in secrets
    assert "jwt_secret" in secrets


def test_every_real_secret_ref_resolves() -> None:
    """Every `secret` ref used by a real manifest resolves to a generation spec.

    A ref doesn't have to be pre-registered in shared_secrets.yml (see
    resolve_secret_spec's fallback) — this just confirms nothing raises.
    """
    manifests = discover_manifests(_REPO_ROOT)
    shared_secrets = load_shared_secrets(_SHARED_SECRETS_PATH)

    for ref in collect_secret_refs(manifests):
        resolve_secret_spec(ref, shared_secrets)
