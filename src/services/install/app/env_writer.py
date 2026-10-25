"""Resolves secrets and writes every discovered manifest's .env file.

The one invariant that matters here: a secret already written to disk is
never regenerated. Postgres's own data directory is initialized with
whatever password it saw on first boot — silently swapping that password on
a rerun would desync it from the already-initialized volume and break the
service outright, not just rotate a credential.
"""

from pathlib import Path

from app.discovery import DiscoveredManifest, resolve_secret_spec
from app.schema import SharedSecretSpec
from app.secrets import generate_secret


def read_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file.

    Args:
        path: path to the .env file. A missing file yields an empty dict.

    Returns:
        dict[str, str]: parsed key/value pairs — blank lines and lines
            starting with '#' are skipped.
    """
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def resolve_existing_secrets(manifests: list[DiscoveredManifest]) -> dict[str, str]:
    """Find secret values already written to disk by an earlier run.

    Args:
        manifests: manifests returned by `discover_manifests`.

    Returns:
        dict[str, str]: secret ref -> the value already present on disk, for
            every ref that has one written anywhere. A ref missing from this
            dict simply hasn't been written yet.
    """
    found: dict[str, str] = {}
    for discovered in manifests:
        existing = read_env_file(discovered.env_path)
        for key, var in discovered.manifest.vars.items():
            if var.source != "secret" or var.ref in found:
                continue
            if existing.get(key):
                found[var.ref] = existing[key]
    return found


def resolve_secrets(
    manifests: list[DiscoveredManifest], shared_secrets: dict[str, SharedSecretSpec]
) -> dict[str, str]:
    """Resolve a value for every secret ref referenced across all manifests.

    Reuses whatever is already on disk (see `resolve_existing_secrets`) and
    generates a fresh value only for a ref that isn't written anywhere yet.

    Args:
        manifests: manifests returned by `discover_manifests`.
        shared_secrets: the parsed shared_secrets.yml registry.

    Returns:
        dict[str, str]: secret ref -> its resolved value.
    """
    refs = {
        var.ref
        for discovered in manifests
        for var in discovered.manifest.vars.values()
        if var.source == "secret" and var.ref is not None
    }
    resolved = resolve_existing_secrets(manifests)
    for ref in refs - resolved.keys():
        spec = resolve_secret_spec(ref, shared_secrets)
        resolved[ref] = generate_secret(spec.length)
    return resolved


def render_env_content(
    discovered: DiscoveredManifest, secrets: dict[str, str], form_values: dict[str, str]
) -> str:
    """Render one manifest's .env file content.

    Args:
        discovered: the manifest and its target directory.
        secrets: resolved secret ref -> value (see `resolve_secrets`).
        form_values: submitted form field -> value.

    Returns:
        str: the full .env content, one KEY=VALUE line per var, in the
            manifest's own declared order.

    Raises:
        KeyError: if a 'secret' var's ref has no resolved value, or a
            required 'form' var has no submitted value and no default.
    """
    lines = []
    for key, var in discovered.manifest.vars.items():
        if var.source == "fixed":
            value = var.value
        elif var.source == "secret":
            value = secrets[var.ref]
        else:
            value = form_values.get(var.field)
            if value is None:
                if var.default is not None:
                    value = var.default
                elif var.required:
                    raise KeyError(f"missing required form field: {var.field}")
                else:
                    value = ""
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def is_fully_configured(discovered: DiscoveredManifest) -> bool:
    """Check whether a manifest's .env already has every required value set.

    Lets the wizard recognize a hand-configured deployment and skip straight
    to the stub page instead of asking the user to fill the form again.

    Args:
        discovered: the manifest and its target directory.

    Returns:
        bool: True if every secret and every required form var already has
            a non-empty value in the existing .env file.
    """
    existing = read_env_file(discovered.env_path)
    for key, var in discovered.manifest.vars.items():
        if var.source == "fixed":
            continue
        if var.source == "form" and not var.required:
            continue
        if not existing.get(key):
            return False
    return True


def write_env_files(
    manifests: list[DiscoveredManifest],
    shared_secrets: dict[str, SharedSecretSpec],
    form_values: dict[str, str],
) -> None:
    """Resolve every secret and write every manifest's .env file to disk.

    Args:
        manifests: manifests returned by `discover_manifests`.
        shared_secrets: the parsed shared_secrets.yml registry.
        form_values: submitted form field -> value.
    """
    secrets = resolve_secrets(manifests, shared_secrets)
    for discovered in manifests:
        content = render_env_content(discovered, secrets, form_values)
        discovered.env_path.write_text(content, encoding="utf-8")
