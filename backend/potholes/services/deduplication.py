from collections import Counter, defaultdict
import hashlib
import math

from django.db import connection, transaction

from potholes.models import Pothole, PotholeObservation


def rebuild_consolidated_potholes(eps_meters: float = 2.5) -> int:
    """Rebuild managed Pothole rows from all georeferenced observations."""
    if not math.isfinite(eps_meters) or eps_meters <= 0:
        raise ValueError("eps_meters debe ser un número mayor que cero.")
    if connection.vendor != "postgresql":
        raise RuntimeError("La deduplicación espacial requiere PostgreSQL/PostGIS.")

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(527438291)")
        observations = list(
            PotholeObservation.objects.filter(location__isnull=False)
            .only("id", "severity", "confidence_avg", "confidence_max", "timestamp",
                  "location", "evidence_path")
            .order_by("id")
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id,
                       ST_ClusterDBSCAN(
                           ST_Transform(location, 32721),
                           %s,
                           1
                       ) OVER (
                           ORDER BY id
                           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                       ) AS cluster_id
                FROM potholes_potholeobservation
                WHERE location IS NOT NULL
                ORDER BY id
                """,
                [eps_meters],
            )
            cluster_by_id = dict(cursor.fetchall())

        groups = defaultdict(list)
        for observation in observations:
            groups[cluster_by_id[observation.id]].append(observation)

        PotholeObservation.objects.filter(cluster__isnull=False).update(cluster=None)
        active_keys = set()
        for members in groups.values():
            member_ids = sorted(item.pk for item in members)
            consolidation_key = hashlib.sha256(
                ",".join(str(item_id) for item_id in member_ids).encode("ascii")
            ).hexdigest()
            active_keys.add(consolidation_key)
            representative = max(
                members,
                key=lambda item: (item.confidence_avg, item.confidence_max, item.timestamp),
            )
            votes = Counter(item.severity for item in members)
            confidence_by_severity = defaultdict(float)
            for item in members:
                confidence_by_severity[item.severity] += item.confidence_avg
            severity = min(
                votes,
                key=lambda value: (-votes[value], -confidence_by_severity[value], value),
            )
            latitude = sum(item.location.y for item in members) / len(members)
            longitude = sum(item.location.x for item in members) / len(members)
            pothole, _ = Pothole.objects.update_or_create(
                consolidation_key=consolidation_key,
                defaults={
                    "gravedad": severity,
                    "radio_estimado": 0.5,
                    "latitud": latitude,
                    "longitud": longitude,
                    "confianza": representative.confidence_avg,
                    "timestamp_deteccion": representative.timestamp,
                    "evidence_path": representative.evidence_path,
                    "is_consolidated": True,
                },
            )
            PotholeObservation.objects.filter(pk__in=member_ids).update(
                cluster=pothole
            )
        stale = Pothole.objects.filter(is_consolidated=True)
        if active_keys:
            stale = stale.exclude(consolidation_key__in=active_keys)
        stale.delete()
    return len(groups)