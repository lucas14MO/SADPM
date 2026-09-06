from django.db import models
from django.utils import timezone


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bache"
        verbose_name_plural = "Baches"
        ordering = ['-timestamp_deteccion']

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
