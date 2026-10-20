"""Tests for manifest discovery across a repo tree."""

from pathlib import Path

import pytest
import yaml

from app.discovery import (
    ManifestError,
    collect_secret_refs,
    discover_manifests,
    load_shared_secrets,
    resolve_secret_spec,
)
from app.schema import SharedSecretSpec


def _write_yaml(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(content), encoding="utf-8")


def test_discovers_manifests_from_deploy_and_services(tmp_path: Path) -> None:
    """Both deploy/install.yml and src/services/*/install.yml are picked up."""
    _write_yaml(
        tmp_path / "deploy" / "install.yml",
        {"vars": {"POSTGRES_USER": {"source": "fixed", "value": "telemax"}}},
    )
    _write_yaml(
        tmp_path / "src" / "services" / "identity" / "install.yml",
        {"vars": {"JWT_SECRET": {"source": "secret", "ref": "jwt_secret"}}},
    )
    # A service directory with no install.yml must simply be ignored.
    (tmp_path / "src" / "services" / "nginx").mkdir(parents=True)

    discovered = discover_manifests(tmp_path)

    service_dirs = {d.service_dir.name for d in discovered}
    assert service_dirs == {"deploy", "identity"}


def test_env_path_is_always_service_dir_slash_env(tmp_path: Path) -> None:
    """The target .env path is never declared in install.yml — it's implicit."""
    _write_yaml(
        tmp_path / "src" / "services" / "identity" / "install.yml",
        {"vars": {"JWT_SECRET": {"source": "secret", "ref": "jwt_secret"}}},
    )

    [discovered] = discover_manifests(tmp_path)

    assert discovered.env_path == tmp_path / "src" / "services" / "identity" / ".env"


def test_invalid_manifest_raises_manifest_error_naming_the_file(tmp_path: Path) -> None:
    """A malformed install.yml fails loudly, naming its own path."""
    bad_path = tmp_path / "src" / "services" / "identity" / "install.yml"
    _write_yaml(bad_path, {"vars": {"JWT_SECRET": {"source": "secret"}}})  # missing ref

    with pytest.raises(ManifestError) as exc_info:
        discover_manifests(tmp_path)

    assert "install.yml" in str(exc_info.value)


def test_load_shared_secrets_parses_registry(tmp_path: Path) -> None:
    """shared_secrets.yml entries parse into SharedSecretSpec objects."""
    path = tmp_path / "shared_secrets.yml"
    _write_yaml(path, {"jwt_secret": {"type": "random_token", "length": 48}})

    secrets = load_shared_secrets(path)

    assert secrets["jwt_secret"].length == 48


def test_collect_secret_refs_deduplicates_across_manifests(tmp_path: Path) -> None:
    """The same ref used by two services counts once, not twice."""
    _write_yaml(
        tmp_path / "src" / "services" / "identity" / "install.yml",
        {"vars": {"JWT_SECRET": {"source": "secret", "ref": "jwt_secret"}}},
    )
    _write_yaml(
        tmp_path / "src" / "services" / "api-gateway" / "install.yml",
        {"vars": {"JWT_SECRET": {"source": "secret", "ref": "jwt_secret"}}},
    )

    refs = collect_secret_refs(discover_manifests(tmp_path))

    assert refs == {"jwt_secret"}


def test_resolve_secret_spec_falls_back_when_unregistered() -> None:
    """An unregistered secret ref still resolves, via a generic default."""
    spec = resolve_secret_spec("encryption_master_key", shared_secrets={})

    assert spec.type == "random_token"
    assert spec.length == 32


def test_resolve_secret_spec_prefers_the_registry_entry() -> None:
    """A registered secret's own length/type wins over the generic default."""
    registry = {"jwt_secret": SharedSecretSpec(type="random_token", length=48)}

    spec = resolve_secret_spec("jwt_secret", registry)

    assert spec.length == 48
