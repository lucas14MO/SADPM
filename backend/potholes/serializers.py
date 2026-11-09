from rest_framework import serializers
from .models import Pothole, PotholeFeedback, PotholeObservation


class PotholeSerializer(serializers.ModelSerializer):
    coordenadas = serializers.ReadOnlyField()
    url_imagen = serializers.ReadOnlyField()
    false_positive_reports = serializers.SerializerMethodField()
    repaired_reports = serializers.SerializerMethodField()

    @staticmethod
    def get_false_positive_reports(instance):
        return getattr(instance, "feedback_false_positive_count", instance.false_positive_reports)

    @staticmethod
    def get_repaired_reports(instance):
        return getattr(instance, "feedback_repaired_count", instance.repaired_reports)

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


class PotholeObservationClassificationSerializer(serializers.ModelSerializer):
    session_key = serializers.CharField(source="session.session_key", read_only=True)
    classified_by_username = serializers.CharField(
        source="classified_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = PotholeObservation
        fields = [
            "id",
            "session_key",
            "track_id",
            "severity",
            "human_severity",
            "area_norm",
            "confidence_avg",
            "frames_detected",
            "timestamp",
            "evidence_image",
            "classified_by_username",
            "classified_at",
        ]
        read_only_fields = [
            "id", "session_key", "track_id", "severity", "area_norm",
            "confidence_avg", "frames_detected", "timestamp", "evidence_image",
            "classified_by_username", "classified_at",
        ]
