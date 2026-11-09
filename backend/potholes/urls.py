from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PotholeObservationClassificationViewSet, PotholeViewSet

router = DefaultRouter()
router.register(r'baches', PotholeViewSet, basename='bache')
router.register(r'potholes', PotholeViewSet, basename='pothole')
router.register(
    r'observaciones/clasificacion',
    PotholeObservationClassificationViewSet,
    basename='observacion-clasificacion',
)

urlpatterns = [
    path('', include(router.urls)),
]
