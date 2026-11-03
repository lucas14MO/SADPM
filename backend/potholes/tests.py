import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from potholes.models import CaptureSession, Pothole, PotholeObservation
from potholes.management.commands.import_processed_potholes import Command


class ImportValidationTests(SimpleTestCase):
    def test_rejects_out_of_range_coordinates(self):
        record = SpatialDatabaseTests._record(1, 91, -55.86)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CommandError):
                Command()._validate_record(record, Path(directory))

    def test_rejects_average_confidence_above_maximum(self):
        record = SpatialDatabaseTests._record(1, -27.33, -55.86)
        record["confidence_avg"] = 0.95
        record["confidence_max"] = 0.9
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CommandError):
                Command()._validate_record(record, Path(directory))

    def test_rejects_evidence_path_outside_session(self):
        record = SpatialDatabaseTests._record(1, -27.33, -55.86)
        record["evidence_image"] = "../../outside.jpg"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CommandError):
                Command()._validate_record(record, Path(directory).resolve())


class SpatialDatabaseTests(TestCase):
    databases = {"default"}

    def setUp(self):
        from django.db import connection

        if connection.vendor != "postgresql":
            self.skipTest("Estas pruebas requieren PostgreSQL/PostGIS.")

    def _create_session_dir(self, name, records):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        session_dir = Path(temporary.name) / name
        session_dir.mkdir()
        (session_dir / "processed_potholes.json").write_text(
            json.dumps(records), encoding="utf-8"
        )
        return session_dir

    @staticmethod
    def _record(track_id, latitude, longitude):
        return {
            "track_id": track_id,
            "severity": "pothole_moderate",
            "confidence_avg": 0.8,
            "confidence_max": 0.9,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": "2026-10-26T12:00:00+00:00",
            "frame_key": 12,
            "frames_detected": 4,
            "evidence_image": "",
        }

    def _import_session(self, name, records):
        session_dir = self._create_session_dir(name, records)
        call_command("import_processed_potholes", str(session_dir), verbosity=0)
        return session_dir

    def test_import_is_idempotent_and_keeps_cluster_primary_key_stable(self):
        run_a = self._create_session_dir("run-a", [self._record(1, -27.33, -55.86)])
        call_command("import_processed_potholes", str(run_a), verbosity=0)
        self._import_session("run-b", [self._record(1, -27.330005, -55.86)])

        self.assertEqual(CaptureSession.objects.count(), 2)
        self.assertEqual(PotholeObservation.objects.count(), 2)
        self.assertEqual(Pothole.objects.filter(is_consolidated=True).count(), 1)
        self.assertEqual(PotholeObservation.objects.filter(cluster__isnull=False).count(), 2)
        cluster_id = Pothole.objects.get(is_consolidated=True).pk

        call_command("import_processed_potholes", str(run_a), verbosity=0)

        self.assertEqual(PotholeObservation.objects.count(), 2)
        self.assertEqual(Pothole.objects.filter(is_consolidated=True).count(), 1)
        self.assertEqual(Pothole.objects.get(is_consolidated=True).pk, cluster_id)

    def test_distant_and_unlocated_observations_remain_separate_or_unclustered(self):
        self._import_session("near", [self._record(1, -27.33, -55.86)])
        self._import_session("far", [self._record(1, -27.331, -55.86)])
        self._import_session("no-gps", [self._record(1, None, None)])

        self.assertEqual(Pothole.objects.filter(is_consolidated=True).count(), 2)
        self.assertEqual(
            PotholeObservation.objects.filter(
                location__isnull=True, cluster__isnull=True
            ).count(),
            1,
        )

    def test_invalid_record_rolls_back_session_and_observations(self):
        invalid = self._record(2, 100, -55.86)
        session_dir = self._create_session_dir(
            "invalid-run", [self._record(1, -27.33, -55.86), invalid]
        )

        with self.assertRaises(CommandError):
            call_command("import_processed_potholes", str(session_dir), verbosity=0)

        self.assertEqual(CaptureSession.objects.count(), 0)
        self.assertEqual(PotholeObservation.objects.count(), 0)

    def test_api_rejects_nonfinite_or_out_of_range_spatial_filters(self):
        client = APIClient()
        for params in (
            {"lat": "nan", "lng": "-55.86", "radio": "100"},
            {"lat": "-27.33", "lng": "-55.86", "radio": "inf"},
            {"lat": "91", "lng": "-55.86", "radio": "100"},
            {"lat": "-27.33", "lng": "-55.86", "radio": "-1"},
        ):
            with self.subTest(params=params):
                response = client.get(reverse("bache-list"), params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, [])

    def test_radius_filter_preserves_public_api_contract(self):
        Pothole.objects.create(
            gravedad="leve", latitud=-27.33, longitud=-55.86, confianza=0.8
        )
        Pothole.objects.create(
            gravedad="critico", latitud=-27.34, longitud=-55.86, confianza=0.9
        )

        response = APIClient().get(
            reverse("bache-list"), {"lat": "-27.33", "lng": "-55.86", "radio": "100"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn("latitud", response.data[0])
        self.assertIn("longitud", response.data[0])
        self.assertIn("gravedad", response.data[0])

    def test_rebuild_keeps_manually_created_potholes(self):
        manual = Pothole.objects.create(
            gravedad="leve", latitud=-27.33, longitud=-55.86, confianza=0.8
        )
        self._import_session("one-detection", [self._record(1, -27.33, -55.86)])

        manual.refresh_from_db()
        self.assertFalse(manual.is_consolidated)
        self.assertTrue(Pothole.objects.filter(pk=manual.pk).exists())
