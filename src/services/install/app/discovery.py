"""Finds every install.yml in the repo and parses it against the schema.

This is the single extension point mentioned in the design: a brand-new
microservice becomes installable by adding one install.yml next to its own
Dockerfile — nothing here needs to change or know its name in advance.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.schema import ServiceManifest, SharedSecretSpec

_DEFAULT_SECRET_LENGTH = 32


class ManifestError(Exception):
    """Raised when an install.yml or shared_secrets.yml fails validation."""


@dataclass
class DiscoveredManifest:
    """A parsed install.yml together with the directory that owns it."""

    service_dir: Path
    manifest: ServiceManifest

    @property
    def env_path(self) -> Path:
        """Path of the .env file this manifest's variables should populate.

        Returns:
            Path: always `<service_dir>/.env` — never declared explicitly in
                install.yml, so every manifest follows the same convention.
        """
        return self.service_dir / ".env"


def discover_manifests(repo_root: Path) -> list[DiscoveredManifest]:
    """Find and parse every install.yml under the repo.

    Args:
        repo_root: absolute path to the repository root.

    Returns:
        list[DiscoveredManifest]: one entry per discovered install.yml,
            sorted by directory path for deterministic output.

    Raises:
        ManifestError: if a discovered file fails schema validation.
    """
    candidates = sorted(repo_root.glob("deploy/install.yml")) + sorted(
        repo_root.glob("src/services/*/install.yml")
    )
    discovered = []
    for path in candidates:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            manifest = ServiceManifest.model_validate(raw)
        except Exception as exc:
            raise ManifestError(f"{path}: {exc}") from exc
        discovered.append(
            DiscoveredManifest(service_dir=path.parent, manifest=manifest)
        )
    return discovered


def load_shared_secrets(path: Path) -> dict[str, SharedSecretSpec]:
    """Parse shared_secrets.yml.

    Args:
        path: path to shared_secrets.yml.

    Returns:
        dict[str, SharedSecretSpec]: secret name -> its generation spec.

    Raises:
        ManifestError: if the file fails schema validation.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {
            name: SharedSecretSpec.model_validate(spec) for name, spec in raw.items()
        }
    except Exception as exc:
        raise ManifestError(f"{path}: {exc}") from exc


def collect_secret_refs(manifests: list[DiscoveredManifest]) -> set[str]:
    """Collect every distinct `secret` ref used across all manifests.

    Args:
        manifests: manifests returned by `discover_manifests`.

    Returns:
        set[str]: the union of every `ref` from a `source: secret` variable.
    """
    return {
        var.ref
        for discovered in manifests
        for var in discovered.manifest.vars.values()
        if var.source == "secret" and var.ref is not None
    }


def resolve_secret_spec(
    ref: str, shared_secrets: dict[str, SharedSecretSpec]
) -> SharedSecretSpec:
    """Look up a secret's generation spec, falling back to a generic default.

    A secret used by only one service doesn't have to be pre-registered in
    shared_secrets.yml — only cross-service secrets need an entry there.

    Args:
        ref: the secret name, as referenced by a manifest's `ref` field.
        shared_secrets: the parsed shared_secrets.yml registry.

    Returns:
        SharedSecretSpec: the registered spec, or a 32-byte random_token
            default if `ref` isn't registered.
    """
    default = SharedSecretSpec(type="random_token", length=_DEFAULT_SECRET_LENGTH)
    return shared_secrets.get(ref, default)
