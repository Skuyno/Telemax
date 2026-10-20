"""Tests for install.yml/shared_secrets.yml validation rules."""

import pytest
from pydantic import ValidationError

from app.schema import ServiceManifest, SharedSecretSpec, VarSpec


def test_fixed_source_accepts_a_value() -> None:
    """A 'fixed' source carries its literal value through unchanged."""
    spec = VarSpec(source="fixed", value="http://identity:8000")
    assert spec.value == "http://identity:8000"


def test_fixed_source_without_value_is_rejected() -> None:
    """A 'fixed' source with no value is a malformed manifest."""
    with pytest.raises(ValidationError):
        VarSpec(source="fixed")


def test_secret_source_without_ref_is_rejected() -> None:
    """A 'secret' source needs a ref to know which secret to use."""
    with pytest.raises(ValidationError):
        VarSpec(source="secret")


def test_form_source_without_field_is_rejected() -> None:
    """A 'form' source needs a field name to collect from the user."""
    with pytest.raises(ValidationError):
        VarSpec(source="form")


def test_service_manifest_parses_a_mix_of_sources() -> None:
    """A manifest can mix fixed/secret/form vars in one file."""
    manifest = ServiceManifest.model_validate(
        {
            "vars": {
                "POSTGRES_DB": {"source": "fixed", "value": "telemax_identity"},
                "JWT_SECRET": {"source": "secret", "ref": "jwt_secret"},
                "SUPERUSER_USERNAME": {
                    "source": "form",
                    "field": "superuser_username",
                    "required": True,
                },
            }
        }
    )
    assert manifest.vars["POSTGRES_DB"].value == "telemax_identity"
    assert manifest.vars["JWT_SECRET"].ref == "jwt_secret"
    assert manifest.vars["SUPERUSER_USERNAME"].required is True


def test_shared_secret_spec_requires_positive_length() -> None:
    """A zero/negative-length secret spec makes no sense and is rejected."""
    with pytest.raises(ValidationError):
        SharedSecretSpec(type="random_token", length=0)
