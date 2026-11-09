from django import forms
from django.contrib import admin
from django.db.models import Count, Q
import uuid
from .models import Pothole, PotholeFeedback, PotholeObservation


class PotholeFeedbackInlineForm(forms.ModelForm):
    class Meta:
        model = PotholeFeedback
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["client_token"].initial = uuid.uuid4()


class PotholeFeedbackInline(admin.TabularInline):
    model = PotholeFeedback
    form = PotholeFeedbackInlineForm
    extra = 1
    fields = ("feedback_type", "client_token", "created_at")
    readonly_fields = ("created_at",)


def refresh_pothole_feedback_counts(pothole):
    counts = pothole.feedback.aggregate(
        false_positive=Count("id", filter=Q(feedback_type=PotholeFeedback.FALSE_POSITIVE)),
        repaired=Count("id", filter=Q(feedback_type=PotholeFeedback.REPAIRED)),
    )
    pothole.false_positive_reports = counts["false_positive"]
    pothole.repaired_reports = counts["repaired"]
    pothole.is_visible = pothole.false_positive_reports < 3 and pothole.repaired_reports == 0
    pothole.save(update_fields=[
        "false_positive_reports", "repaired_reports", "is_visible", "updated_at"
    ])


@admin.register(Pothole)
class PotholeAdmin(admin.ModelAdmin):
    inlines = (PotholeFeedbackInline,)
    list_display = (
        "id", "gravedad", "false_positive_reports", "repaired_reports",
        "is_visible", "is_consolidated", "updated_at",
    )
    list_filter = ("gravedad", "is_visible", "is_consolidated")
    search_fields = ("id", "latitud", "longitud")
    fields = (
        "gravedad", "radio_estimado", "latitud", "longitud", "confianza",
        "area_norm", "timestamp_deteccion", "imagen", "url_imagen_externa",
        "false_positive_reports", "repaired_reports", "is_visible",
        "is_consolidated", "consolidation_key",
    )
    readonly_fields = (
        "area_norm", "false_positive_reports", "repaired_reports", "is_visible",
        "is_consolidated", "consolidation_key",
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        refresh_pothole_feedback_counts(form.instance)


@admin.register(PotholeFeedback)
class PotholeFeedbackAdmin(admin.ModelAdmin):
    list_display = ("pothole", "feedback_type", "client_token", "created_at")
    list_filter = ("feedback_type",)
    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        old_pothole_id = None
        if change:
            old_pothole_id = PotholeFeedback.objects.get(pk=obj.pk).pothole_id
        super().save_model(request, obj, form, change)
        if old_pothole_id and old_pothole_id != obj.pothole_id:
            refresh_pothole_feedback_counts(Pothole.objects.get(pk=old_pothole_id))
        refresh_pothole_feedback_counts(obj.pothole)

    def delete_model(self, request, obj):
        pothole = obj.pothole
        super().delete_model(request, obj)
        refresh_pothole_feedback_counts(pothole)

    def delete_queryset(self, request, queryset):
        pothole_ids = set(queryset.values_list("pothole_id", flat=True))
        super().delete_queryset(request, queryset)
        for pothole in Pothole.objects.filter(pk__in=pothole_ids):
            refresh_pothole_feedback_counts(pothole)


@admin.register(PotholeObservation)
class PotholeObservationAdmin(admin.ModelAdmin):
    list_display = ("session", "track_id", "severity", "human_severity", "timestamp")
    list_filter = ("severity", "human_severity")
