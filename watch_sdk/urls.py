"""watch_sdk URL Configuration

The `urlpatterns` list routes URLs to  For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, re_path

from watch_sdk.views.shared import *
from watch_sdk.views.apple_healthkit import upload_health_data_using_json_file
from watch_sdk.views.fitbit import *
from watch_sdk.views.google_fit import *
from watch_sdk.views.strava import *

app_name = "watch_sdk"

urlpatterns = [
    path("generate_key", generate_key),
    path("upload_health_data_as_json", upload_health_data_using_json_file),
    path(
        "user",
        UserViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "user/<int:pk>",
        UserViewSet.as_view({"get": "retrieve", "put": "update"}),
    ),
    path(
        "user_app_from_key",
        UserAppFromKeyViewSet.as_view(),
    ),
    path(
        "user_app",
        UserAppViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "user_app/<int:pk>",
        UserAppViewSet.as_view({"get": "retrieve", "put": "update"}),
    ),
    path("platform", PlatformViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "platform/<int:pk>",
        PlatformViewSet.as_view({"get": "retrieve", "put": "update"}),
    ),
    path("enable_platform", enable_platform_for_app),
    path("enable_datatype", enable_datatype_for_app),
    path(
        "test_webhook_data",
        WebhookDataViewSet.as_view({"get": "list"}),
    ),
    path("debug_webhook_logs", DebugWebhookLogsViewSet.as_view({"get": "list"})),
    path("data_type", DataTypeViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "fitbit_notification_log",
        FitbitNotificationLogViewSet.as_view({"get": "list"}),
    ),
    path("check_watch_connection", watch_connection_exists),
    path("connect_platform_for_user", connect_platform_for_user),
    path("watch_connection", WatchConnectionListView.as_view()),
    path("watch_connection/<int:pk>", WatchConnectionUpdateView.as_view()),
    path("sync_google_fit_data", sync_from_google_fit),
    path("debug_test_strava", debug_test_strava),
    path("test_sync", test_google_sync),
    path("test_webhook", test_webhook_endpoint),
    path("analyze_webhook_data", analyze_webhook_data),
    path("test_fitbit", test_fitbit_integration),
    path("fitbit/<int:pk>/webhook", FitbitWebhook.as_view()),
    path("strava/<int:pk>/webhook", StravaWebhook.as_view()),
]
