from watch_sdk.models import User, UserApp


def get_user_app(user: User):
    created_apps = UserApp.objects.filter(user=user)
    if created_apps.exists():
        return created_apps.first()

    accessed_apps = UserApp.objects.filter(access_users=user)
    if accessed_apps.exists():
        return accessed_apps.first()

    return None
