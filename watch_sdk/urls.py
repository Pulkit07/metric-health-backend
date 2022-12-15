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
    path("make_connection", views.make_connection),
    path("generate_key", views.generate_key),
    path("check_connection", views.check_connection),
    path("upload_health_data", views.upload_health_data),
    path(
        "user",
        views.UserViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "user/<int:pk>",
        views.UserViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
            }
        ),
    ),
    path(
        "user_app",
        views.UserAppViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path(
        "user_app/<int:pk>",
        views.UserAppViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
            }
        ),
    ),
    path(
        "fitness_data",
        views.FitnessDataViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
    ),
    path("sync_google_fit_data", views.SyncGoogleFitApi.as_view()),
]
