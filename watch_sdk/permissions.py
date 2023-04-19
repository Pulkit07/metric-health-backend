# permission classes for various views
from rest_framework import permissions
from watch_sdk.utils import firebase as firebase_utils

from watch_sdk.models import UserApp


class ValidKeyPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # TODO: remove the key from query params once all current users are migrated
        # to passing it as headers
        key = (
            request.query_params.get("key")
            if request.query_params.get("key")
            else request.META.get("key")
        )
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
        email = firebase_utils.verify_firebase_token(auth_token)
        return True if email else False


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # TODO: Change this to a more secure method
        if request.META.get("HTTP_ADMIN_PASSWORD") == "admin":
            return True
        return False
