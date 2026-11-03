import json
import hashlib
import math
import csv
from datetime import datetime
from pathlib import Path

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from potholes.models import CaptureSession, PotholeObservation
from potholes.services.deduplication import rebuild_consolidated_potholes


SEVERITY_MAP = {
    "pothole_light": "leve",
    "pothole_moderate": "moderado",
    "pothole_critical": "critico",
}


class Command(BaseCommand):
    help = "Importa processed_potholes.json y actualiza la deduplicación espacial."

    def add_arguments(self, parser):
        parser.add_argument("session_dir", type=Path)
        parser.add_argument("--eps-meters", type=float, default=2.5)

    def handle(self, *args, **options):
        session_dir = options["session_dir"].resolve()
        eps_meters = options["eps_meters"]
        input_path = session_dir / "processed_potholes.json"
        if not input_path.is_file():
            raise CommandError(f"No existe el archivo {input_path}")
        if not math.isfinite(eps_meters) or eps_meters <= 0:
            raise CommandError("--eps-meters debe ser un número mayor que cero.")

        try:
            records = json.loads(input_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"No se pudo leer el JSON: {exc}") from exc
        if not isinstance(records, list):
            raise CommandError("processed_potholes.json debe contener una lista.")

        session_metadata = {}
        metadata_path = session_dir / "session.json"
        if metadata_path.is_file():
            try:
                session_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CommandError(f"session.json no es JSON válido: {exc}") from exc
            if not isinstance(session_metadata, dict):
                raise CommandError("session.json debe contener un objeto JSON.")
        session_start = session_metadata.get("start_utc")
        if not session_start:
            frames_path = session_dir / "frames.csv"
            try:
                with frames_path.open("r", newline="", encoding="utf-8-sig") as source:
                    session_start = next(csv.DictReader(source))["utc"]
            except (OSError, StopIteration, KeyError) as exc:
                raise CommandError(
                    "Se requiere session.json.start_utc o un frames.csv con timestamp UTC."
                ) from exc

        imported = 0
        session_identity = json.dumps(
            {
                "name": session_dir.name,
                "start_utc": session_start,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        session_key = (
            f"{session_dir.name[:180]}-"
            f"{hashlib.sha256(session_identity.encode('utf-8')).hexdigest()[:16]}"
        )
        with transaction.atomic():
            capture_session, _ = CaptureSession.objects.update_or_create(
                session_key=session_key,
                defaults={"source_path": str(session_dir), "metadata": session_metadata},
            )
            seen_track_ids = set()
            for record in records:
                validated = self._validate_record(record, session_dir)
                track_id = validated["track_id"]
                if track_id in seen_track_ids:
                    raise CommandError(f"track_id duplicado en JSON: {track_id}")
                seen_track_ids.add(track_id)
                PotholeObservation.objects.update_or_create(
                    session=capture_session,
                    track_id=track_id,
                    defaults=validated,
                )
                imported += 1

            if seen_track_ids:
                capture_session.observations.exclude(track_id__in=seen_track_ids).delete()
            else:
                capture_session.observations.all().delete()
            cluster_count = rebuild_consolidated_potholes(eps_meters)

        self.stdout.write(self.style.SUCCESS(
            f"Sesión {capture_session.session_key}: {imported} observaciones; "
            f"{cluster_count} baches consolidados (eps={eps_meters:g} m)."
        ))

    def _validate_record(self, record, session_dir):
        if not isinstance(record, dict):
            raise CommandError("Cada elemento del JSON debe ser un objeto.")
        try:
            track_id = int(record["track_id"])
            model_severity = record["severity"]
            severity = SEVERITY_MAP[model_severity]
            confidence_avg = float(record["confidence_avg"])
            confidence_max = float(record["confidence_max"])
            frames_detected = int(record["frames_detected"])
            frame_key = int(record["frame_key"])
            timestamp = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise CommandError(f"Registro incompleto o inválido: {exc}") from exc
        if track_id < 0 or frame_key < 0 or frames_detected <= 0:
            raise CommandError("track_id/frame_key deben ser no negativos y frames_detected positivo.")
        if not all(math.isfinite(value) and 0 <= value <= 1
                   for value in (confidence_avg, confidence_max)):
            raise CommandError("Las confianzas deben estar entre 0 y 1.")
        if confidence_avg > confidence_max:
            raise CommandError("confidence_avg no puede superar confidence_max.")
        if timezone.is_naive(timestamp):
            raise CommandError("timestamp debe incluir zona horaria.")
        latitude, longitude = record.get("latitude"), record.get("longitude")
        if (latitude is None) != (longitude is None):
            raise CommandError("latitude y longitude deben ser ambos nulos o ambos numéricos.")
        location = None
        if latitude is not None:
            try:
                latitude, longitude = float(latitude), float(longitude)
            except (TypeError, ValueError) as exc:
                raise CommandError("latitude y longitude deben ser numéricas.") from exc
            if not (math.isfinite(latitude) and -90 <= latitude <= 90):
                raise CommandError("latitude fuera de rango.")
            if not (math.isfinite(longitude) and -180 <= longitude <= 180):
                raise CommandError("longitude fuera de rango.")
            location = Point(longitude, latitude, srid=4326)

        evidence_path = ""
        relative_evidence = record.get("evidence_image")
        if relative_evidence:
            if not isinstance(relative_evidence, str):
                raise CommandError("evidence_image debe ser una ruta relativa de texto.")
            candidate = (session_dir / relative_evidence).resolve()
            if not candidate.is_relative_to(session_dir):
                raise CommandError("evidence_image debe permanecer dentro de la sesión.")
            if not candidate.is_file():
                raise CommandError(f"No existe la evidencia indicada: {relative_evidence}")
            evidence_path = str(candidate)

        return {
            "severity": severity,
            "confidence_avg": confidence_avg,
            "confidence_max": confidence_max,
            "frames_detected": frames_detected,
            "timestamp": timestamp,
            "frame_key": frame_key,
            "location": location,
            "evidence_path": evidence_path,
        }