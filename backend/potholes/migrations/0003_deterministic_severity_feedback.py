import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("potholes", "0002_postgis_observations"),
    ]

    operations = [
        migrations.AddField(
            model_name="potholeobservation",
            name="area_norm",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="potholeobservation",
            name="evidence_image",
            field=models.ImageField(blank=True, null=True,
                                    upload_to="pothole_observations/"),
        ),
        migrations.AddConstraint(
            model_name="potholeobservation",
            constraint=models.CheckConstraint(
                condition=models.Q(area_norm__isnull=True) | models.Q(area_norm__gte=0),
                name="observation_area_norm_nonnegative",
            ),
        ),
        migrations.AddField(
            model_name="pothole",
            name="area_norm",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pothole",
            name="false_positive_reports",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="pothole",
            name="repaired_reports",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="pothole",
            name="is_visible",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddConstraint(
            model_name="pothole",
            constraint=models.CheckConstraint(
                condition=models.Q(area_norm__isnull=True) | models.Q(area_norm__gte=0),
                name="pothole_area_norm_nonnegative",
            ),
        ),
        migrations.CreateModel(
            name="PotholeFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                            serialize=False, verbose_name="ID")),
                ("feedback_type", models.CharField(
                    choices=[("false_positive", "Falso positivo"),
                             ("repaired", "Reparado o desactualizado")],
                    max_length=20,
                )),
                ("client_token", models.UUIDField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("pothole", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="feedback",
                    to="potholes.pothole",
                )),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="potholefeedback",
            constraint=models.UniqueConstraint(
                fields=("pothole", "feedback_type", "client_token"),
                name="unique_pothole_feedback_token",
            ),
        ),
    ]