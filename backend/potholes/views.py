import math
from django.db.models import QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Pothole
from .serializers import PotholeSerializer


def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia del gran círculo en metros entre dos puntos
    en la Tierra (latitud, longitud en grados decimales).
    """
    R = 6371000.0  # Radio medio de la Tierra en metros

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


class PotholeViewSet(viewsets.ModelViewSet):
    """
    API endpoint para consultar, crear y administrar baches.

    Filtros soportados por Query Params:
    - lat: Latitud del centro de búsqueda (ej. -27.33056)
    - lng: Longitud del centro de búsqueda (ej. -55.86667)
    - radio: Radio de búsqueda en metros (ej. 500)
    - gravedad: Filtrar por nivel de gravedad ('leve', 'moderado', 'critico')
    """
    queryset = Pothole.objects.all()
    serializer_class = PotholeSerializer

    def get_queryset(self) -> QuerySet[Pothole]:  # type: ignore[override]
        queryset = Pothole.objects.all()

        # Filtrado opcional por gravedad
        gravedad = self.request.GET.get('gravedad', None)
        if gravedad:
            queryset = queryset.filter(gravedad__iexact=gravedad)

        # Filtrado espacial por radio de búsqueda (lat, lng, radio)
        lat_param = self.request.GET.get('lat', None)
        lng_param = self.request.GET.get('lng', None)
        radio_param = self.request.GET.get('radio', None)

        if lat_param is not None and lng_param is not None:
            try:
                center_lat = float(lat_param)
                center_lng = float(lng_param)
                radius_meters = float(radio_param) if radio_param is not None else 1000.0

                # Pre-filtrado por bounding box aproximado (1 grado ~ 111 km)
                delta_lat = radius_meters / 111000.0
                # Ajuste de longitud por latitud
                cos_lat = math.cos(math.radians(center_lat))
                delta_lng = radius_meters / (111000.0 * max(abs(cos_lat), 0.00001))

                queryset = queryset.filter(
                    latitud__gte=center_lat - delta_lat,
                    latitud__lte=center_lat + delta_lat,
                    longitud__gte=center_lng - delta_lng,
                    longitud__lte=center_lng + delta_lng
                )

                # Filtrado exacto con Haversine
                filtered_ids = []
                for bache in queryset:
                    dist = haversine_distance_meters(center_lat, center_lng, bache.latitud, bache.longitud)
                    if dist <= radius_meters:
                        filtered_ids.append(bache.pk)

                queryset = Pothole.objects.filter(id__in=filtered_ids)
            except (ValueError, TypeError):
                pass

        return queryset
