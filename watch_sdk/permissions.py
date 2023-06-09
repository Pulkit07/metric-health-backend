# permission classes for various views
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import permissions
from watch_sdk.utils import firebase as firebase_utils

from watch_sdk.models import User, UserApp


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
        self.email = firebase_utils.verify_firebase_token(auth_token)
        return True if self.email else False


class AppAuthPermission(FirebaseAuthPermission):
    def has_object_permission(self, request, view, obj):
        """
        Checking the app permission for logged in user(via token)
        Object permission get checked only after 'has_permission' so using the token's email from there.
        """
        try:
            user = User.objects.get(email=self.email)
            if user == obj.user or user in obj.access_users.all():
                return True
            return False
        except ObjectDoesNotExist:
            return False


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # TODO: Change this to a more secure method
        if request.META.get("HTTP_ADMIN_PASSWORD") == "admin":
            return True
        return False
