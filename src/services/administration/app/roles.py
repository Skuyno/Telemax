"""Role constants and role-based account management rules.

This is a deliberate duplicate of identity's app/roles.py: administration
has no database of its own (it's a stateless orchestrator in front of
identity's /internal/accounts API), so it can't import identity's Python
module across a process/service boundary. Keep the two copies in sync if
this table ever changes — the same duplication pattern already exists
between the Python services and ws-gateway's Go copy of NATS subjects.
"""

SUPERUSER = "superuser"
ADMIN = "admin"
USER = "user"

# Which roles a caller with a given role is allowed to create or delete.
# superuser can manage admins and regular users; admin can only manage
# regular users; a plain user can't manage anyone. The superuser role
# itself is never in any of these sets — it's provisioned once at
# identity's own startup and can't be created or removed through account
# management at all (identity enforces that as a hard invariant too, not
# just relying on this table).
MANAGEABLE_ROLES: dict[str, set[str]] = {
    SUPERUSER: {ADMIN, USER},
    ADMIN: {USER},
}
