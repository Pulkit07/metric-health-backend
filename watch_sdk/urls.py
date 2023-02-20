"""watch_sdk URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, re_path
from . import views

app_name = "watch_sdk"

urlpatterns = [
    path("generate_key", views.generate_key),
    path("upload_health_data", views.upload_health_data),
    path("upload_health_data_as_json", views.upload_health_data_using_json_file),
    path(
        "user",
        views.UserViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "user/<int:pk>",
        views.UserViewSet.as_view({"get": "retrieve", "put": "update"}),
    ),
    path(
        "user_app_from_key",
        views.UserAppFromKeyViewSet.as_view(),
    ),
    path(
        "user_app",
        views.UserAppViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "user_app/<int:pk>",
        views.UserAppViewSet.as_view({"get": "retrieve", "put": "update"}),
    ),
    path("platform", views.PlatformViewSet.as_view({"get": "list", "post": "create"})),
    path(
        "platform/<int:pk>",
        views.PlatformViewSet.as_view({"get": "retrieve", "put": "update"}),
    ),
    path("enable_platform", views.enable_platform_for_app),
    path("enable_datatype", views.enable_datatype_for_app),
    path(
        "fitness_data",
        views.FitnessDataViewSet.as_view({"get": "list", "post": "create"}),
    ),
    path(
        "test_webhook_data",
        views.WebhookDataViewSet.as_view({"get": "list"}),
    ),
    path("data_type", views.DataTypeViewSet.as_view({"get": "list", "post": "create"})),
    path("check_watch_connection", views.watch_connection_exists),
    path("connect_platform_for_user", views.connect_platform_for_user),
    path("watch_connection", views.WatchConnectionListView.as_view()),
    path("watch_connection/<int:pk>", views.WatchConnectionUpdateView.as_view()),
    path("sync_google_fit_data", views.sync_from_google_fit),
    path("test_sync", views.test_google_sync),
    path("test_webhook", views.test_webhook_endpoint),
    path("test_fitbit", views.test_fitbit_integration),
]
