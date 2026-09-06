from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from potholes.models import Pothole


class Command(BaseCommand):
    help = 'Siembra baches sintéticos de prueba en la ciudad de Encarnación (Paraguay)'

    def handle(self, *args, **options):
        # Limpiar baches existentes si se desea
        # Pothole.objects.all().delete()

        # Coordenadas base en Encarnación, Paraguay (Centro / Costanera / Ruta 1 / Ruta 6)
        SAMPLE_BACHES = [
            {
                "gravedad": "critico",
                "radio_estimado": 1.2,
                "latitud": -27.33056,
                "longitud": -55.86667,
                "confianza": 0.94,
                "url_imagen_externa": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "moderado",
                "radio_estimado": 0.7,
                "latitud": -27.33210,
                "longitud": -55.86450,
                "confianza": 0.88,
                "url_imagen_externa": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "leve",
                "radio_estimado": 0.4,
                "latitud": -27.32890,
                "longitud": -55.86910,
                "confianza": 0.79,
                "url_imagen_externa": "https://images.unsplash.com/photo-1578991624414-276ef23a534f?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "critico",
                "radio_estimado": 1.5,
                "latitud": -27.33540,
                "longitud": -55.86120,
                "confianza": 0.96,
                "url_imagen_externa": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "moderado",
                "radio_estimado": 0.8,
                "latitud": -27.32500,
                "longitud": -55.87200,
                "confianza": 0.85,
                "url_imagen_externa": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "leve",
                "radio_estimado": 0.3,
                "latitud": -27.33810,
                "longitud": -55.85800,
                "confianza": 0.82,
                "url_imagen_externa": "https://images.unsplash.com/photo-1578991624414-276ef23a534f?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "critico",
                "radio_estimado": 1.1,
                "latitud": -27.32980,
                "longitud": -55.86330,
                "confianza": 0.91,
                "url_imagen_externa": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=600&auto=format&fit=crop"
            },
            {
                "gravedad": "moderado",
                "radio_estimado": 0.6,
                "latitud": -27.33390,
                "longitud": -55.86800,
                "confianza": 0.87,
                "url_imagen_externa": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop"
            }
        ]

        now = timezone.now()
        created_count = 0

        for idx, item in enumerate(SAMPLE_BACHES):
            timestamp = now - timedelta(days=random.randint(0, 10), hours=random.randint(1, 12))
            bache, created = Pothole.objects.get_or_create(
                latitud=item["latitud"],
                longitud=item["longitud"],
                defaults={
                    "gravedad": item["gravedad"],
                    "radio_estimado": item["radio_estimado"],
                    "confianza": item["confianza"],
                    "timestamp_deteccion": timestamp,
                    "url_imagen_externa": item["url_imagen_externa"]
                }
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Sembrado completado: {created_count} baches nuevos creados (Total en BD: {Pothole.objects.count()}).')
        )
