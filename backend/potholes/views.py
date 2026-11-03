from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import QuerySet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Pothole
from .serializers import PotholeSerializer


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
            severities = [value.strip() for value in gravedad.split(",") if value.strip()]
            if len(severities) > 1:
                queryset = queryset.filter(gravedad__in=severities)
            elif severities:
                queryset = queryset.filter(gravedad__iexact=severities[0])

        # Filtrado espacial por radio de búsqueda (lat, lng, radio)
        lat_param = self.request.GET.get('lat', None)
        lng_param = self.request.GET.get('lng', None)
        radio_param = self.request.GET.get('radio', None)

        if lat_param is not None and lng_param is not None:
            try:
                center_lat = float(lat_param)
                center_lng = float(lng_param)
                radius_meters = float(radio_param) if radio_param is not None else 1000.0
                if not (
                    math.isfinite(center_lat)
                    and math.isfinite(center_lng)
                    and -90 <= center_lat <= 90
                    and -180 <= center_lng <= 180
                ):
                    return queryset.none()
                if not math.isfinite(radius_meters) or radius_meters < 0:
                    return queryset.none()
                center = Point(center_lng, center_lat, srid=4326)
                queryset = queryset.filter(location__dwithin=(center, D(m=radius_meters)))
            except (ValueError, TypeError):
                return queryset.none()

        return queryset
