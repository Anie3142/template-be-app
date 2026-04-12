"""Example app URL routes."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExampleChildViewSet, ExampleParentViewSet
from .webhooks import example_webhook

router = DefaultRouter()
router.register('parents', ExampleParentViewSet, basename='example-parent')
router.register('children', ExampleChildViewSet, basename='example-child')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook', example_webhook),
]
