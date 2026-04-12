"""Core URL routes — health check lives here."""
from django.urls import path

from .views import health_check

urlpatterns = [
    path('health', health_check),
]
