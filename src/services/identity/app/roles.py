"""Role constants and role-based account management rules."""

SUPERUSER = "superuser"
ADMIN = "admin"
USER = "user"

ALL_ROLES = {SUPERUSER, ADMIN, USER}

# Which roles a caller with a given role is allowed to create or delete.
# superuser can manage admins and regular users; admin can only manage
# regular users; a plain user can't manage anyone. The superuser role
# itself is never in any of these sets — it's provisioned once at
# startup (see app/users/service.py) and can't be created or removed
# through the account-management endpoints at all.
MANAGEABLE_ROLES: dict[str, set[str]] = {
    SUPERUSER: {ADMIN, USER},
    ADMIN: {USER},
}
