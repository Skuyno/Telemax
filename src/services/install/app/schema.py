"""Pydantic models for install.yml and shared_secrets.yml manifests."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class VarSpec(BaseModel):
    """One environment variable entry inside a service's install.yml."""

    source: Literal["fixed", "secret", "form"]
    value: str | None = None
    ref: str | None = None
    field: str | None = None
    label: str | None = None
    input_type: str = "text"
    required: bool = False
    default: str | None = None

    @model_validator(mode="after")
    def _check_source_has_its_required_fields(self) -> "VarSpec":
        """Reject a spec missing the field its own source needs.

        Returns:
            VarSpec: this instance, unchanged, once validated.

        Raises:
            ValueError: if the declared source is missing a field it requires
                (e.g. "fixed" without "value").
        """
        if self.source == "fixed" and self.value is None:
            raise ValueError("source 'fixed' requires 'value'")
        if self.source == "secret" and self.ref is None:
            raise ValueError("source 'secret' requires 'ref'")
        if self.source == "form" and self.field is None:
            raise ValueError("source 'form' requires 'field'")
        return self


class ServiceManifest(BaseModel):
    """Parsed install.yml for a single service."""

    vars: dict[str, VarSpec]


class SharedSecretSpec(BaseModel):
    """One entry in shared_secrets.yml."""

    type: Literal["random_token"]
    length: int = Field(gt=0)
