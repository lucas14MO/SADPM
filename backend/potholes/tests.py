import json
import tempfile
import uuid
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from potholes.models import CaptureSession, Pothole, PotholeFeedback, PotholeObservation
from potholes.management.commands.import_processed_potholes import Command


class ImportValidationTests(SimpleTestCase):
    def test_accepts_canonical_severity_and_area_norm(self):
        record = SpatialDatabaseTests._record(1, -27.33, -55.86)
        record["severity"] = "moderado"
        record["area_norm"] = 0.0125

        with tempfile.TemporaryDirectory() as directory:
            validated = Command()._validate_record(record, Path(directory))

        self.assertEqual(validated["severity"], "moderado")
        self.assertEqual(validated["area_norm"], 0.0125)

    def test_rejects_invalid_area_norm(self):
        for area_norm in (-0.1, float("nan"), float("inf")):
            with self.subTest(area_norm=area_norm):
                record = SpatialDatabaseTests._record(1, -27.33, -55.86)
                record["area_norm"] = area_norm
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaises(CommandError):
                        Command()._validate_record(record, Path(directory))

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
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
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
        (session_dir / "session.json").write_text(
            json.dumps({"start_utc": "2026-10-26T12:00:00+00:00"}), encoding="utf-8"
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
        old_cluster_id = Pothole.objects.get(is_consolidated=True).pk
        feedback_token = uuid.uuid4()
        PotholeFeedback.objects.create(
            pothole_id=old_cluster_id,
            feedback_type=PotholeFeedback.FALSE_POSITIVE,
            client_token=feedback_token,
        )
        self._import_session("run-b", [self._record(1, -27.330005, -55.86)])
        cluster_id = Pothole.objects.get(is_consolidated=True).pk

        self.assertEqual(CaptureSession.objects.count(), 2)
        self.assertEqual(PotholeObservation.objects.count(), 2)
        self.assertEqual(Pothole.objects.filter(is_consolidated=True).count(), 1)
        self.assertEqual(PotholeObservation.objects.filter(cluster__isnull=False).count(), 2)
        self.assertTrue(PotholeFeedback.objects.filter(
            pothole_id=cluster_id, client_token=feedback_token
        ).exists())

        call_command("import_processed_potholes", str(run_a), verbosity=0)

        self.assertEqual(PotholeObservation.objects.count(), 2)
        self.assertEqual(Pothole.objects.filter(is_consolidated=True).count(), 1)
        self.assertEqual(Pothole.objects.get(is_consolidated=True).pk, cluster_id)
        self.assertTrue(PotholeFeedback.objects.filter(
            pothole_id=cluster_id, client_token=feedback_token
        ).exists())

    def test_import_persists_evidence_in_media_and_sets_cluster_image(self):
        record = self._record(1, -27.33, -55.86)
        record["severity"] = "moderado"
        record["area_norm"] = 0.02
        record["evidence_image"] = "crops/bache_0001.jpg"
        session_dir = self._create_session_dir("evidence-run", [record])
        crop = session_dir / "crops" / "bache_0001.jpg"
        crop.parent.mkdir()
        crop.write_bytes(b"synthetic-image-fixture")

        call_command("import_processed_potholes", str(session_dir), verbosity=0)

        observation = PotholeObservation.objects.get(track_id=1)
        pothole = Pothole.objects.get(is_consolidated=True)
        self.assertTrue(observation.evidence_image)
        self.assertTrue(observation.evidence_image.storage.exists(observation.evidence_image.name))
        self.assertEqual(pothole.imagen.name, observation.evidence_image.name)
        self.assertTrue(pothole.imagen.storage.exists(pothole.imagen.name))

    def test_feedback_survives_cluster_split_without_duplication(self):
        run_a = self._create_session_dir("split-a", [self._record(1, -27.33, -55.86)])
        run_b = self._create_session_dir("split-b", [self._record(1, -27.330005, -55.86)])
        call_command("import_processed_potholes", str(run_a), verbosity=0)
        call_command("import_processed_potholes", str(run_b), verbosity=0)
        old_cluster = Pothole.objects.get(is_consolidated=True)
        tokens = [uuid.uuid4() for _ in range(3)]
        PotholeFeedback.objects.bulk_create([
            PotholeFeedback(
                pothole=old_cluster,
                feedback_type=PotholeFeedback.FALSE_POSITIVE,
                client_token=token,
            )
            for token in tokens
        ])

        record = self._record(1, -27.34, -55.86)
        (run_b / "processed_potholes.json").write_text(json.dumps([record]), encoding="utf-8")
        call_command("import_processed_potholes", str(run_b), verbosity=0)

        clusters = list(Pothole.objects.filter(is_consolidated=True).order_by("pk"))
        self.assertEqual(len(clusters), 2)
        self.assertEqual(PotholeFeedback.objects.count(), 3)
        feedback_target_ids = set(PotholeFeedback.objects.values_list("pothole_id", flat=True))
        self.assertEqual(len(feedback_target_ids), 1)
        target = next(cluster for cluster in clusters if cluster.pk in feedback_target_ids)
        other = next(cluster for cluster in clusters if cluster.pk not in feedback_target_ids)
        target.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(target.false_positive_reports, 3)
        self.assertFalse(target.is_visible)
        self.assertTrue(other.is_visible)

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

    def test_feedback_is_idempotent_and_hides_after_three_false_positive_reports(self):
        pothole = Pothole.objects.create(
            gravedad="moderado", latitud=-27.33, longitud=-55.86, confianza=0.8
        )
        url = reverse("bache-feedback", args=[pothole.pk])
        client = APIClient()
        tokens = [str(uuid.uuid4()) for _ in range(3)]

        first = client.post(url, {
            "feedback_type": PotholeFeedback.FALSE_POSITIVE,
            "client_token": tokens[0],
        }, format="json")
        duplicate = client.post(url, {
            "feedback_type": PotholeFeedback.FALSE_POSITIVE,
            "client_token": tokens[0],
        }, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.data["false_positive_reports"], 1)

        for token in tokens[1:]:
            response = client.post(url, {
                "feedback_type": PotholeFeedback.FALSE_POSITIVE,
                "client_token": token,
            }, format="json")
            self.assertEqual(response.status_code, 201)

        pothole.refresh_from_db()
        self.assertEqual(pothole.false_positive_reports, 3)
        self.assertFalse(pothole.is_visible)
        self.assertEqual(client.get(reverse("bache-list")).data, [])

    def test_rebuild_keeps_manually_created_potholes(self):
        manual = Pothole.objects.create(
            gravedad="leve", latitud=-27.33, longitud=-55.86, confianza=0.8
        )
        self._import_session("one-detection", [self._record(1, -27.33, -55.86)])

        manual.refresh_from_db()
        self.assertFalse(manual.is_consolidated)
        self.assertTrue(Pothole.objects.filter(pk=manual.pk).exists())

    def test_recalculate_severity_updates_observations_and_clusters_only(self):
        session = CaptureSession.objects.create(
            session_key="severity-calibration",
            source_path="/tmp/severity-calibration",
        )
        observation = PotholeObservation.objects.create(
            session=session,
            track_id=1,
            severity="leve",
            confidence_avg=0.8,
            confidence_max=0.9,
            area_norm=0.02,
            frames_detected=3,
            timestamp="2026-10-26T12:00:00+00:00",
            frame_key=10,
            location=Point(-55.86, -27.33, srid=4326),
        )
        manual = Pothole.objects.create(
            gravedad="leve", latitud=-27.34, longitud=-55.86, confianza=0.7
        )

        call_command(
            "recalcular_severidad", light_threshold=0.01,
            critical_threshold=0.05, verbosity=0,
        )

        observation.refresh_from_db()
        cluster = Pothole.objects.get(is_consolidated=True)
        self.assertEqual(observation.severity, "moderado")
        self.assertEqual(cluster.gravedad, "moderado")

        call_command(
            "recalcular_severidad", light_threshold=0.001,
            critical_threshold=0.005, dry_run=True, verbosity=0,
        )
        observation.refresh_from_db()
        self.assertEqual(observation.severity, "moderado")

        call_command(
            "recalcular_severidad", light_threshold=0.001,
            critical_threshold=0.005, verbosity=0,
        )
        observation.refresh_from_db()
        cluster.refresh_from_db()
        manual.refresh_from_db()
        self.assertEqual(observation.severity, "critico")
        self.assertEqual(cluster.gravedad, "critico")
        self.assertEqual(manual.gravedad, "leve")

    def test_classification_api_requires_staff_and_records_classifier(self):
        session = CaptureSession.objects.create(
            session_key="classification-test", source_path="/tmp/classification-test"
        )
        observation = PotholeObservation.objects.create(
            session=session,
            track_id=1,
            severity="moderado",
            confidence_avg=0.8,
            confidence_max=0.9,
            area_norm=0.02,
            frames_detected=3,
            timestamp="2026-10-26T12:00:00+00:00",
            frame_key=10,
            evidence_image="pothole_observations/crop.jpg",
        )
        endpoint = reverse("observacion-clasificacion-list")
        anonymous = APIClient()
        self.assertEqual(anonymous.get(endpoint).status_code, 403)

        user_model = get_user_model()
        regular_user = user_model.objects.create_user(username="regular")
        regular_client = APIClient()
        regular_client.force_authenticate(user=regular_user)
        self.assertEqual(regular_client.get(endpoint).status_code, 403)

        staff_user = user_model.objects.create_user(username="calibrator", is_staff=True)
        staff_client = APIClient()
        staff_client.force_authenticate(user=staff_user)
        response = staff_client.get(endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["area_norm"], 0.02)

        updated = staff_client.patch(
            reverse("observacion-clasificacion-detail", args=[observation.pk]),
            {"human_severity": "critico"},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        observation.refresh_from_db()
        self.assertEqual(observation.human_severity, "critico")
        self.assertEqual(observation.classified_by, staff_user)
        self.assertIsNotNone(observation.classified_at)
