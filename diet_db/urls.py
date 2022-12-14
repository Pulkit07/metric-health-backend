from django.urls import path
from . import views

app_name = 'diet_db'

urlpatterns = [
    # add urls for all viewsets defined in views.py
    path('dish', views.DishViewSet.as_view({
        'get': 'list',
        'post': 'create',
    })),
    path('dish/<int:pk>', views.DishViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'delete': 'destroy',
    })),
]
