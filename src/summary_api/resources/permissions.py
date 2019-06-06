from rest_framework import permissions


class DefaultPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in list(permissions.SAFE_METHODS) + ['POST']:
            return True
        else:
            return False
