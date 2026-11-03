from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations, models
import django.db.models.deletion


def populate_existing_locations(apps, schema_editor):
    Pothole = apps.get_model("potholes", "Pothole")
    table = schema_editor.quote_name(Pothole._meta.db_table)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} "
            "SET location = ST_SetSRID(ST_MakePoint(longitud, latitud), 4326)::geography"
        )


def restore_existing_coordinates(apps, schema_editor):
    Pothole = apps.get_model("potholes", "Pothole")
    table = schema_editor.quote_name(Pothole._meta.db_table)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {table} "
            "SET latitud = ST_Y(location::geometry), longitud = ST_X(location::geometry) "
            "WHERE location IS NOT NULL"
        )


def validate_existing_potholes(apps, schema_editor):
    Pothole = apps.get_model("potholes", "Pothole")
    invalid_coordinates = Pothole.objects.filter(
        models.Q(latitud__lt=-90) | models.Q(latitud__gt=90)
        | models.Q(longitud__lt=-180) | models.Q(longitud__gt=180)
        | models.Q(confianza__lt=0) | models.Q(confianza__gt=1)
    )
    if invalid_coordinates.exists():
        raise RuntimeError(
            "No se puede migrar: hay baches con latitud/longitud/confianza fuera de rango. "
            "Corrige esos registros antes de repetir migrate."
        )


class Migration(migrations.Migration):
    dependencies = [("potholes", "0001_initial")]

    operations = [
        CreateExtension("postgis"),
        migrations.AddField(
            model_name="pothole",
            name="location",
            field=gis_models.PointField(
                geography=True, null=True, blank=True, spatial_index=True, srid=4326
            ),
        ),
        migrations.AddField(
            model_name="pothole",
            name="is_consolidated",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="pothole",
            name="evidence_path",
            field=models.CharField(blank=True, max_length=1024),
        ),
        migrations.AddField(
            model_name="pothole",
            name="consolidation_key",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(validate_existing_potholes, migrations.RunPython.noop),
        migrations.RunPython(populate_existing_locations, restore_existing_coordinates),
        migrations.AddConstraint(
            model_name="pothole",
            constraint=models.CheckConstraint(
                condition=models.Q(latitud__gte=-90, latitud__lte=90),
                name="pothole_latitude_valid_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="pothole",
            constraint=models.CheckConstraint(
                condition=models.Q(longitud__gte=-180, longitud__lte=180),
                name="pothole_longitude_valid_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="pothole",
            constraint=models.CheckConstraint(
                condition=models.Q(confianza__gte=0, confianza__lte=1),
                name="pothole_confidence_0_1",
            ),
        ),
        migrations.CreateModel(
            name="CaptureSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(max_length=255, unique=True)),
                ("source_path", models.CharField(max_length=1024)),
                ("imported_at", models.DateTimeField(auto_now=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={"ordering": ["session_key"]},
        ),
        migrations.CreateModel(
            name="PotholeObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("track_id", models.PositiveIntegerField()),
                ("severity", models.CharField(choices=[("leve", "Leve"),
                    ("moderado", "Moderado"), ("critico", "Crítico")], max_length=20)),
                ("confidence_avg", models.FloatField()),
                ("confidence_max", models.FloatField()),
                ("frames_detected", models.PositiveIntegerField(default=1)),
                ("timestamp", models.DateTimeField()),
                ("frame_key", models.PositiveIntegerField()),
                ("location", gis_models.PointField(blank=True, null=True, spatial_index=True,
                                                    srid=4326)),
                ("evidence_path", models.CharField(blank=True, max_length=1024)),
                ("cluster", models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="observations", to="potholes.pothole")),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="observations", to="potholes.capturesession")),
            ],
        ),
        migrations.AddConstraint(
            model_name="potholeobservation",
            constraint=models.UniqueConstraint(fields=("session", "track_id"),
                name="unique_session_track_observation"),
        ),
        migrations.AddConstraint(
            model_name="potholeobservation",
            constraint=models.CheckConstraint(condition=models.Q(
                confidence_avg__gte=0, confidence_avg__lte=1),
                name="observation_avg_confidence_0_1"),
        ),
        migrations.AddConstraint(
            model_name="potholeobservation",
            constraint=models.CheckConstraint(condition=models.Q(
                confidence_max__gte=0, confidence_max__lte=1),
                name="observation_max_confidence_0_1"),
        ),
        migrations.AddConstraint(
            model_name="potholeobservation",
            constraint=models.CheckConstraint(
                condition=models.Q(confidence_avg__lte=models.F("confidence_max")),
                name="observation_avg_lte_max_confidence",
            ),
        ),
        migrations.AddConstraint(
            model_name="potholeobservation",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(location__isnull=True)
                    | (
                        models.lookups.GreaterThanOrEqual(
                            models.Func(models.F("location"), function="ST_Y"),
                            models.Value(-90),
                        )
                        & models.lookups.LessThanOrEqual(
                            models.Func(models.F("location"), function="ST_Y"),
                            models.Value(90),
                        )
                        & models.lookups.GreaterThanOrEqual(
                            models.Func(models.F("location"), function="ST_X"),
                            models.Value(-180),
                        )
                        & models.lookups.LessThanOrEqual(
                            models.Func(models.F("location"), function="ST_X"),
                            models.Value(180),
                        )
                    )
                ),
                name="observation_location_valid_range",
            ),
        ),
        migrations.AddIndex(
            model_name="potholeobservation",
            index=models.Index(fields=["timestamp"], name="potholes_obs_timestamp_idx"),
        ),
    ]