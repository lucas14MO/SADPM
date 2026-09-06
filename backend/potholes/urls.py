from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PotholeViewSet

router = DefaultRouter()
router.register(r'baches', PotholeViewSet, basename='bache')
router.register(r'potholes', PotholeViewSet, basename='pothole')

urlpatterns = [
    path('', include(router.urls)),
]
