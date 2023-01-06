# permission classes for various views
from rest_framework import permissions

from watch_sdk.models import UserApp

class ValidKeyPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        key = request.query_params.get("key")
        if not key:
            return False
        try:
            UserApp.objects.get(key=key)
        except Exception:
            return False
        return True