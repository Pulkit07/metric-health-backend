from django.core.exceptions import ObjectDoesNotExist

from watch_sdk.models import User, UserApp

from .firebase import verify_firebase_token


def get_user_app(user: User):
    created_apps = UserApp.objects.filter(user=user)
    if created_apps.exists():
        return created_apps.first()

    accessed_apps = UserApp.objects.filter(access_users=user)
    if accessed_apps.exists():
        return accessed_apps.first()

    return None


def get_user_from_token(request):
    auth_token = request.META.get("HTTP_AUTHORIZATION")
    if not auth_token:
        return None

    email = verify_firebase_token(auth_token)
    try:
        user = User.objects.get(email=email)
        return user
    except ObjectDoesNotExist:
        return None
