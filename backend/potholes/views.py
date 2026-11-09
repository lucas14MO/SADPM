import math

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db import connection, transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from .models import Pothole, PotholeFeedback, PotholeObservation
from .serializers import (
    PotholeFeedbackSerializer,
    PotholeObservationClassificationSerializer,
    PotholeSerializer,
)


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
        queryset = Pothole.objects.filter(is_visible=True)

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

    @action(detail=True, methods=["post"], url_path="feedback", permission_classes=[AllowAny])
    def feedback(self, request, pk=None):
        serializer = PotholeFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(527438291)")
            pothole = get_object_or_404(
                Pothole.objects.select_for_update().filter(is_visible=True), pk=pk
            )
            _, created = PotholeFeedback.objects.get_or_create(
                pothole=pothole,
                feedback_type=serializer.validated_data["feedback_type"],
                client_token=serializer.validated_data["client_token"],
            )
            pothole.false_positive_reports = PotholeFeedback.objects.filter(
                pothole=pothole, feedback_type=PotholeFeedback.FALSE_POSITIVE
            ).count()
            pothole.repaired_reports = PotholeFeedback.objects.filter(
                pothole=pothole, feedback_type=PotholeFeedback.REPAIRED
            ).count()
            pothole.is_visible = (
                pothole.false_positive_reports < 3 and pothole.repaired_reports == 0
            )
            pothole.save(update_fields=[
                "false_positive_reports", "repaired_reports", "is_visible"
            ])

        return Response(
            {
                "created": created,
                "false_positive_reports": pothole.false_positive_reports,
                "repaired_reports": pothole.repaired_reports,
                "is_visible": pothole.is_visible,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PotholeObservationClassificationViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PotholeObservationClassificationSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self) -> QuerySet[PotholeObservation]:
        return (
            PotholeObservation.objects.select_related("session", "classified_by")
            .filter(area_norm__isnull=False, evidence_image__isnull=False)
            .exclude(evidence_image="")
            .order_by("human_severity", "id")
        )

    def perform_update(self, serializer):
        serializer.save(classified_by=self.request.user, classified_at=timezone.now())
