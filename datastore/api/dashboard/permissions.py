from rest_framework import permissions


class ReadOnly(permissions.BasePermission):
    """
    Always read-only even if authenticated
    """

    def has_object_permission(self, request, view, obj):
        # we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        return False
