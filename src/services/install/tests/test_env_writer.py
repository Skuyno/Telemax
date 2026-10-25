"""Tests for secret resolution and .env writing — idempotency is the point."""

from pathlib import Path

import pytest

from app.discovery import DiscoveredManifest
from app.env_writer import (
    is_fully_configured,
    read_env_file,
    render_env_content,
    resolve_existing_secrets,
    resolve_secrets,
    write_env_files,
)
from app.schema import ServiceManifest, SharedSecretSpec, VarSpec


def _manifest(service_dir: Path, **vars_: VarSpec) -> DiscoveredManifest:
    return DiscoveredManifest(
        service_dir=service_dir, manifest=ServiceManifest(vars=vars_)
    )


def test_render_env_content_covers_all_three_sources(tmp_path: Path) -> None:
    """fixed/secret/form each resolve to their expected value."""
    discovered = _manifest(
        tmp_path,
        POSTGRES_DB=VarSpec(source="fixed", value="telemax_identity"),
        JWT_SECRET=VarSpec(source="secret", ref="jwt_secret"),
        SUPERUSER_USERNAME=VarSpec(
            source="form", field="superuser_username", required=True
        ),
    )

    content = render_env_content(
        discovered,
        secrets={"jwt_secret": "s3cr3t"},
        form_values={"superuser_username": "admin"},
    )

    assert content == (
        "POSTGRES_DB=telemax_identity\nJWT_SECRET=s3cr3t\nSUPERUSER_USERNAME=admin\n"
    )


def test_render_env_content_raises_on_missing_required_form_field(
    tmp_path: Path,
) -> None:
    """A required field with no submitted value and no default fails loudly."""
    discovered = _manifest(
        tmp_path,
        SUPERUSER_USERNAME=VarSpec(
            source="form", field="superuser_username", required=True
        ),
    )

    with pytest.raises(KeyError):
        render_env_content(discovered, secrets={}, form_values={})


def test_render_env_content_falls_back_to_default(tmp_path: Path) -> None:
    """An optional form field with no submitted value uses its default."""
    discovered = _manifest(
        tmp_path,
        ALLOW_REGISTRATION=VarSpec(
            source="form", field="allow_registration", default="true"
        ),
    )

    content = render_env_content(discovered, secrets={}, form_values={})

    assert content == "ALLOW_REGISTRATION=true\n"


def test_read_env_file_skips_blanks_and_comments(tmp_path: Path) -> None:
    """Comments and blank lines in an existing .env don't become keys."""
    path = tmp_path / ".env"
    path.write_text("# comment\n\nJWT_SECRET=abc\n", encoding="utf-8")

    assert read_env_file(path) == {"JWT_SECRET": "abc"}


def test_read_env_file_missing_file_returns_empty_dict(tmp_path: Path) -> None:
    """No .env yet is not an error — just nothing resolved."""
    assert read_env_file(tmp_path / ".env") == {}


def test_resolve_existing_secrets_finds_value_from_any_manifest(
    tmp_path: Path,
) -> None:
    """A secret already written under one service is recognized globally."""
    identity_dir = tmp_path / "identity"
    identity_dir.mkdir()
    (identity_dir / ".env").write_text("JWT_SECRET=already-there\n", encoding="utf-8")
    manifests = [
        _manifest(identity_dir, JWT_SECRET=VarSpec(source="secret", ref="jwt_secret")),
        _manifest(
            tmp_path / "api-gateway",
            JWT_SECRET=VarSpec(source="secret", ref="jwt_secret"),
        ),
    ]

    found = resolve_existing_secrets(manifests)

    assert found == {"jwt_secret": "already-there"}


def test_resolve_secrets_reuses_existing_value_instead_of_regenerating(
    tmp_path: Path,
) -> None:
    """The point: an existing secret must never be overwritten with a new one."""
    deploy_dir = tmp_path / "deploy"
    deploy_dir.mkdir()
    (deploy_dir / ".env").write_text(
        "POSTGRES_PASSWORD=do-not-touch-me\n", encoding="utf-8"
    )
    manifests = [
        _manifest(
            deploy_dir,
            POSTGRES_PASSWORD=VarSpec(source="secret", ref="postgres_password"),
        ),
    ]

    resolved = resolve_secrets(manifests, shared_secrets={})

    assert resolved == {"postgres_password": "do-not-touch-me"}


def test_resolve_secrets_generates_fresh_value_when_absent(tmp_path: Path) -> None:
    """A ref nobody has written yet gets a freshly generated value."""
    manifests = [
        _manifest(tmp_path, JWT_SECRET=VarSpec(source="secret", ref="jwt_secret"))
    ]
    registry = {"jwt_secret": SharedSecretSpec(type="random_token", length=48)}

    resolved = resolve_secrets(manifests, shared_secrets=registry)

    assert resolved["jwt_secret"]
    assert resolved["jwt_secret"] != ""


def test_write_env_files_shares_one_secret_value_across_files(tmp_path: Path) -> None:
    """One generated value for a ref lands identically in every file using it."""
    identity_dir = tmp_path / "identity"
    api_gateway_dir = tmp_path / "api-gateway"
    identity_dir.mkdir()
    api_gateway_dir.mkdir()
    manifests = [
        _manifest(identity_dir, JWT_SECRET=VarSpec(source="secret", ref="jwt_secret")),
        _manifest(
            api_gateway_dir, JWT_SECRET=VarSpec(source="secret", ref="jwt_secret")
        ),
    ]

    write_env_files(manifests, shared_secrets={}, form_values={})

    identity_value = read_env_file(identity_dir / ".env")["JWT_SECRET"]
    api_gateway_value = read_env_file(api_gateway_dir / ".env")["JWT_SECRET"]
    assert identity_value == api_gateway_value
    assert identity_value != ""


def test_write_env_files_is_idempotent_across_two_runs(tmp_path: Path) -> None:
    """Running the writer twice must not change an already-generated secret."""
    deploy_dir = tmp_path / "deploy"
    deploy_dir.mkdir()
    manifests = [
        _manifest(
            deploy_dir,
            POSTGRES_PASSWORD=VarSpec(source="secret", ref="postgres_password"),
        ),
    ]

    write_env_files(manifests, shared_secrets={}, form_values={})
    first_value = read_env_file(deploy_dir / ".env")["POSTGRES_PASSWORD"]

    write_env_files(manifests, shared_secrets={}, form_values={})
    second_value = read_env_file(deploy_dir / ".env")["POSTGRES_PASSWORD"]

    assert first_value == second_value


def test_is_fully_configured_true_when_everything_required_is_set(
    tmp_path: Path,
) -> None:
    """A manually pre-populated .env is recognized as already configured."""
    (tmp_path / ".env").write_text(
        "JWT_SECRET=abc\nSUPERUSER_USERNAME=admin\n", encoding="utf-8"
    )
    discovered = _manifest(
        tmp_path,
        JWT_SECRET=VarSpec(source="secret", ref="jwt_secret"),
        SUPERUSER_USERNAME=VarSpec(
            source="form", field="superuser_username", required=True
        ),
    )

    assert is_fully_configured(discovered) is True


def test_is_fully_configured_false_when_a_secret_is_missing(tmp_path: Path) -> None:
    """No .env at all is obviously not configured."""
    discovered = _manifest(
        tmp_path, JWT_SECRET=VarSpec(source="secret", ref="jwt_secret")
    )

    assert is_fully_configured(discovered) is False


def test_is_fully_configured_ignores_optional_form_fields(tmp_path: Path) -> None:
    """An unset optional form var shouldn't block 'already configured'."""
    (tmp_path / ".env").write_text("JWT_SECRET=abc\n", encoding="utf-8")
    discovered = _manifest(
        tmp_path,
        JWT_SECRET=VarSpec(source="secret", ref="jwt_secret"),
        ALLOW_REGISTRATION=VarSpec(
            source="form", field="allow_registration", default="true"
        ),
    )

    assert is_fully_configured(discovered) is True
