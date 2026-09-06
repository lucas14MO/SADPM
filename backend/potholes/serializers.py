from rest_framework import serializers
from .models import Pothole


class PotholeSerializer(serializers.ModelSerializer):
    coordenadas = serializers.ReadOnlyField()
    url_imagen = serializers.ReadOnlyField()

    class Meta:
        model = Pothole
        fields = [
            'id',
            'gravedad',
            'radio_estimado',
            'latitud',
            'longitud',
            'coordenadas',
            'confianza',
            'timestamp_deteccion',
            'imagen',
            'url_imagen_externa',
            'url_imagen',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Ensure url_imagen returns absolute URL if request in context
        request = self.context.get('request')
        if instance.imagen and request is not None:
            ret['url_imagen'] = request.build_absolute_uri(instance.imagen.url)
        elif instance.url_imagen_externa:
            ret['url_imagen'] = instance.url_imagen_externa
        else:
            ret['url_imagen'] = None
        return ret
