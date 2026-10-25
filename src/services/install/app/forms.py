"""Collects the dynamic form fields declared across every install.yml.

This is what keeps the install page itself extensible: a new service's
`source: form` var shows up here — and on the page — without anyone having
to edit this module or the HTML template.
"""

from dataclasses import dataclass

from app.discovery import DiscoveredManifest


@dataclass
class FormField:
    """One user-facing input, derived from a manifest's `source: form` var."""

    field: str
    label: str
    input_type: str
    required: bool
    default: str | None


def collect_form_fields(manifests: list[DiscoveredManifest]) -> list[FormField]:
    """Collect every distinct form field declared across all manifests.

    The same `field` name declared by more than one manifest is listed only
    once — whichever manifest is encountered first (manifests are already
    sorted by discover_manifests, so this is deterministic).

    Args:
        manifests: manifests returned by `discover_manifests`.

    Returns:
        list[FormField]: one entry per distinct field name, in first-seen
            order.
    """
    seen: dict[str, FormField] = {}
    for discovered in manifests:
        for var in discovered.manifest.vars.values():
            if var.source != "form" or var.field in seen:
                continue
            seen[var.field] = FormField(
                field=var.field,
                label=var.label or var.field,
                input_type=var.input_type,
                required=var.required,
                default=var.default,
            )
    return list(seen.values())
