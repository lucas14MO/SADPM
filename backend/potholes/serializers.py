from rest_framework import serializers
from .models import Pothole, PotholeFeedback


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
            'area_norm',
            'timestamp_deteccion',
            'imagen',
            'url_imagen_externa',
            'url_imagen',
            'false_positive_reports',
            'repaired_reports',
            'is_visible',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'area_norm', 'false_positive_reports', 'repaired_reports',
            'is_visible', 'created_at', 'updated_at',
        ]

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


class PotholeFeedbackSerializer(serializers.Serializer):
    feedback_type = serializers.ChoiceField(
        choices=[item[0] for item in PotholeFeedback.FEEDBACK_TYPES]
    )
    client_token = serializers.UUIDField()
