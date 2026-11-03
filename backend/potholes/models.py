from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.db.models import F, Func, Q, Value
from django.db.models.lookups import GreaterThanOrEqual, LessThanOrEqual


class CaptureSession(models.Model):
    session_key = models.CharField(max_length=255, unique=True)
    source_path = models.CharField(max_length=1024)
    imported_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["session_key"]

    def __str__(self):
        return self.session_key


class PotholeObservation(models.Model):
    SEVERITY_CHOICES = [
        ("leve", "Leve"),
        ("moderado", "Moderado"),
        ("critico", "Crítico"),
    ]

    session = models.ForeignKey(
        CaptureSession, on_delete=models.CASCADE, related_name="observations"
    )
    track_id = models.PositiveIntegerField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    confidence_avg = models.FloatField()
    confidence_max = models.FloatField()
    frames_detected = models.PositiveIntegerField(default=1)
    timestamp = models.DateTimeField()
    frame_key = models.PositiveIntegerField()
    location = models.PointField(srid=4326, null=True, blank=True, spatial_index=True)
    evidence_path = models.CharField(max_length=1024, blank=True)
    cluster = models.ForeignKey(
        "Pothole", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="observations",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "track_id"], name="unique_session_track_observation"
            ),
            models.CheckConstraint(
                condition=models.Q(confidence_avg__gte=0, confidence_avg__lte=1),
                name="observation_avg_confidence_0_1",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence_max__gte=0, confidence_max__lte=1),
                name="observation_max_confidence_0_1",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence_avg__lte=F("confidence_max")),
                name="observation_avg_lte_max_confidence",
            ),
            models.CheckConstraint(
                condition=(
                    Q(location__isnull=True)
                    | (
                        GreaterThanOrEqual(Func(F("location"), function="ST_Y"), Value(-90))
                        & LessThanOrEqual(Func(F("location"), function="ST_Y"), Value(90))
                        & GreaterThanOrEqual(Func(F("location"), function="ST_X"), Value(-180))
                        & LessThanOrEqual(Func(F("location"), function="ST_X"), Value(180))
                    )
                ),
                name="observation_location_valid_range",
            ),
        ]
        indexes = [models.Index(fields=["timestamp"], name="potholes_obs_timestamp_idx")]

    def __str__(self):
        return f"{self.session.session_key} / track {self.track_id}"


class Pothole(models.Model):
    GRAVEDAD_CHOICES = [
        ('leve', 'Leve'),
        ('moderado', 'Moderado'),
        ('critico', 'Crítico'),
    ]

    gravedad = models.CharField(
        max_length=20,
        choices=GRAVEDAD_CHOICES,
        default='leve'
    )
    radio_estimado = models.FloatField(
        help_text="Radio estimado del bache en metros",
        default=0.5
    )
    latitud = models.FloatField(
        help_text="Coordenada de latitud (ej. -27.33056)"
    )
    longitud = models.FloatField(
        help_text="Coordenada de longitud (ej. -55.86667)"
    )
    location = models.PointField(
        srid=4326, geography=True, null=True, blank=True, spatial_index=True
    )
    confianza = models.FloatField(
        help_text="Nivel de confianza de la detección IA (0.0 a 1.0)",
        default=1.0
    )
    timestamp_deteccion = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de detección"
    )
    imagen = models.ImageField(
        upload_to='potholes/',
        null=True,
        blank=True,
        help_text="Foto recortada del bache"
    )
    url_imagen_externa = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL externa opcional de la evidencia visual"
    )
    evidence_path = models.CharField(max_length=1024, blank=True)
    is_consolidated = models.BooleanField(default=False, db_index=True)
    consolidation_key = models.CharField(max_length=64, null=True, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not (-90 <= self.latitud <= 90):
            raise ValueError("latitud debe estar entre -90 y 90.")
        if not (-180 <= self.longitud <= 180):
            raise ValueError("longitud debe estar entre -180 y 180.")
        if not (0 <= self.confianza <= 1):
            raise ValueError("confianza debe estar entre 0 y 1.")
        self.location = Point(self.longitud, self.latitud, srid=4326)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"location"}
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Bache"
        verbose_name_plural = "Baches"
        ordering = ['-timestamp_deteccion']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(latitud__gte=-90, latitud__lte=90),
                name="pothole_latitude_valid_range",
            ),
            models.CheckConstraint(
                condition=models.Q(longitud__gte=-180, longitud__lte=180),
                name="pothole_longitude_valid_range",
            ),
            models.CheckConstraint(
                condition=models.Q(confianza__gte=0, confianza__lte=1),
                name="pothole_confidence_0_1",
            ),
        ]

    def __str__(self):
        return f"Bache #{self.pk} - {self.gravedad} ({self.latitud}, {self.longitud})"

    @property
    def coordenadas(self):
        return {
            'lat': self.latitud,
            'lng': self.longitud
        }

    @property
    def url_imagen(self):
        if self.imagen:
            return self.imagen.url
        if self.url_imagen_externa:
            return self.url_imagen_externa
        return None
