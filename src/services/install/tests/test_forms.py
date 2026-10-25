"""Tests for collecting dynamic form fields across manifests."""

from pathlib import Path

from app.discovery import DiscoveredManifest
from app.forms import collect_form_fields
from app.schema import ServiceManifest, VarSpec


def _manifest(service_dir: Path, **vars_: VarSpec) -> DiscoveredManifest:
    return DiscoveredManifest(
        service_dir=service_dir, manifest=ServiceManifest(vars=vars_)
    )


def test_collects_a_form_field_with_its_label_and_type(tmp_path: Path) -> None:
    """A form var's label/input_type/required are carried into the field."""
    manifests = [
        _manifest(
            tmp_path,
            SUPERUSER_USERNAME=VarSpec(
                source="form",
                field="superuser_username",
                label="Имя суперпользователя",
                required=True,
            ),
        )
    ]

    fields = collect_form_fields(manifests)

    assert len(fields) == 1
    assert fields[0].field == "superuser_username"
    assert fields[0].label == "Имя суперпользователя"
    assert fields[0].input_type == "text"
    assert fields[0].required is True


def test_ignores_fixed_and_secret_vars(tmp_path: Path) -> None:
    """Only `source: form` vars become a visible field — nothing else leaks."""
    manifests = [
        _manifest(
            tmp_path,
            POSTGRES_DB=VarSpec(source="fixed", value="telemax_identity"),
            JWT_SECRET=VarSpec(source="secret", ref="jwt_secret"),
        )
    ]

    assert collect_form_fields(manifests) == []


def test_deduplicates_the_same_field_across_manifests(tmp_path: Path) -> None:
    """Two services declaring the same field name produce one entry, not two."""
    manifests = [
        _manifest(
            tmp_path / "identity",
            ALLOW_REGISTRATION=VarSpec(
                source="form", field="allow_registration", label="A"
            ),
        ),
        _manifest(
            tmp_path / "other",
            ALLOW_REGISTRATION=VarSpec(
                source="form", field="allow_registration", label="B"
            ),
        ),
    ]

    fields = collect_form_fields(manifests)

    assert len(fields) == 1
    assert fields[0].label == "A"


def test_label_falls_back_to_the_field_name_when_absent(tmp_path: Path) -> None:
    """A manifest that skips `label` still produces a usable field."""
    manifests = [
        _manifest(tmp_path, X=VarSpec(source="form", field="custom_key"))
    ]

    fields = collect_form_fields(manifests)

    assert fields[0].label == "custom_key"
