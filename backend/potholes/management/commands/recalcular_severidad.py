import math

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Case, CharField, Value, When

from potholes.models import PotholeObservation
from potholes.services.deduplication import rebuild_consolidated_potholes


DEFAULT_LIGHT_THRESHOLD = 0.001
DEFAULT_CRITICAL_THRESHOLD = 0.005


class Command(BaseCommand):
    help = "Recalcula severidades desde area_norm sin volver a procesar videos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--light-threshold", type=float, default=DEFAULT_LIGHT_THRESHOLD,
            help="area_norm menor a este valor se clasifica como leve.",
        )
        parser.add_argument(
            "--critical-threshold", type=float, default=DEFAULT_CRITICAL_THRESHOLD,
            help="area_norm desde este valor se clasifica como crítico.",
        )
        parser.add_argument("--eps-meters", type=float, default=2.5)
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Muestra cuántas observaciones se actualizarían sin guardar cambios.",
        )

    def handle(self, *args, **options):
        light_threshold = options["light_threshold"]
        critical_threshold = options["critical_threshold"]
        eps_meters = options["eps_meters"]
        if not (
            math.isfinite(light_threshold)
            and math.isfinite(critical_threshold)
            and 0 < light_threshold < critical_threshold
        ):
            raise CommandError(
                "Los umbrales deben ser finitos, positivos y light-threshold "
                "debe ser menor que critical-threshold."
            )
        if not math.isfinite(eps_meters) or eps_meters <= 0:
            raise CommandError("--eps-meters debe ser un número mayor que cero.")

        observations = PotholeObservation.objects.filter(area_norm__isnull=False)
        count = observations.count()
        if options["dry_run"]:
            self.stdout.write(
                f"Dry-run: {count} observaciones con area_norm; no se modificó la base."
            )
            return

        try:
            with transaction.atomic():
                observations.update(
                    severity=Case(
                        When(area_norm__lt=light_threshold, then=Value("leve")),
                        When(area_norm__lt=critical_threshold, then=Value("moderado")),
                        default=Value("critico"),
                        output_field=CharField(),
                    )
                )
                cluster_count = rebuild_consolidated_potholes(eps_meters)
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(
            f"{count} observaciones recalculadas; {cluster_count} baches consolidados "
            f"actualizados (umbrales={light_threshold:g}/{critical_threshold:g}, "
            f"eps={eps_meters:g} m)."
        ))