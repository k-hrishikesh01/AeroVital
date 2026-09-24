from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


def get_user_pilot(user):
    """Retrieve pilot profile associated with a user if present."""
    if user and hasattr(user, "pilot_profile"):
        return user.pilot_profile
    return None


def enforce_pilot_scoping(request, qs, pilot_field="pilot"):
    """Enforces data-level authorization for pilot data.

    - Staff and superusers have global access across all pilots.
    - Authenticated users linked to a pilot profile can only access their own data.
    - If a pilot user explicitly queries another pilot's data, PermissionDenied (403) is raised.
    - Non-pilot users (e.g. operators without a pilot profile) can query data according to permissions.
    """
    if not request.user or not request.user.is_authenticated:
        return qs.none()

    if request.user.is_staff or request.user.is_superuser:
        pilot_id = request.query_params.get("pilot")
        if pilot_id:
            return qs.filter(**{f"{pilot_field}_id": pilot_id})
        return qs

    user_pilot = get_user_pilot(request.user)
    if user_pilot is not None:
        requested_pilot_id = request.query_params.get("pilot")
        if requested_pilot_id and str(requested_pilot_id) != str(user_pilot.id):
            raise PermissionDenied("You do not have permission to access another pilot's records.")
        return qs.filter(**{pilot_field: user_pilot})

    # Unlinked non-staff operator: allow query filtering
    pilot_id = request.query_params.get("pilot")
    if pilot_id:
        return qs.filter(**{f"{pilot_field}_id": pilot_id})
    return qs


class IsStaffOrPilotOwner(permissions.BasePermission):
    """Object-level permission allowing staff global access, and pilots access only to their own profile."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True

        user_pilot = get_user_pilot(request.user)
        if user_pilot is None:
            return True

        # Check if the target object is a Pilot
        if hasattr(obj, "user"):
            return obj.id == user_pilot.id

        # Check if the target object has a foreign key to Pilot
        if hasattr(obj, "pilot"):
            return obj.pilot is not None and obj.pilot.id == user_pilot.id

        return False
