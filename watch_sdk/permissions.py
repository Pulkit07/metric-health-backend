# permission classes for various views
from rest_framework import permissions
from watch_sdk import utils

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


class FirebaseAuthPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        auth_token = request.META.get("HTTP_AUTHORIZATION")
        if not auth_token:
            return False
        return utils.verify_firebase_token(auth_token)


class AdminPermission(permissions.BasePermission):

    def has_permission(self, request, view):
        # TODO: Change this to a more secure method
        if request.META.get("admin_password") == "admin":
            return True
        return False