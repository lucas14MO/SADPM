from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from types import ModuleType

from spm_capture.offline import (
    GPSPoint,
    Observation,
    SeverityConfig,
    TrackSummary,
    interpolate_gps_position,
    load_frame_timestamps,
    process_session,
)


class OfflinePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)

    def test_interpolates_gps_and_returns_none_outside_track(self) -> None:
        points = [
            GPSPoint(self.start, -27.0, -55.0),
            GPSPoint(self.start + timedelta(seconds=10), -26.0, -54.0),
        ]

        self.assertEqual(
            interpolate_gps_position(self.start + timedelta(seconds=5), points),
            (-26.5, -54.5),
        )
        self.assertEqual(interpolate_gps_position(self.start - timedelta(seconds=1), points), (None, None))
        self.assertEqual(interpolate_gps_position(self.start + timedelta(seconds=11), points), (None, None))

    def test_track_uses_largest_roi_box_for_keyframe_and_severity(self) -> None:
        track = TrackSummary(7)
        crop = SimpleNamespace(size=1)
        track.observations = [
            Observation(2, self.start, "pothole", 0.99, (10, 50, 30, 70), crop, (100, 100)),
            Observation(4, self.start + timedelta(seconds=2), "pothole", 0.7,
                        (10, 50, 40, 80), crop, (100, 100)),
            Observation(5, self.start + timedelta(seconds=3), "pothole", 0.8,
                        (10, 50, 40, 80), crop, (100, 100)),
        ]
        config = SeverityConfig(
            light_area_threshold=0.02,
            critical_area_threshold=0.1,
            perspective_reference_ratio=0.65,
        )
        with tempfile.TemporaryDirectory() as directory:
            with patch("spm_capture.offline._save_crop", return_value=True):
                record = track.to_record(3, Path(directory), [], severity_config=config)

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["severity"], "moderado")
        self.assertEqual(record["frame_key"], 5)
        self.assertEqual(record["confidence_max"], 0.99)
        self.assertEqual(record["confidence_keyframe"], 0.8)
        self.assertAlmostEqual(record["confidence_avg"], 0.83)
        self.assertAlmostEqual(record["area_norm"], 0.09)
        self.assertEqual(record["latitude"], None)

    def test_roi_discards_tracks_above_horizon_and_includes_threshold(self) -> None:
        config = SeverityConfig(roi_horizon_ratio=0.45)
        crop = SimpleNamespace(size=1)
        above = Observation(0, self.start, "pothole", 0.9, (0, 20, 20, 40), crop, (100, 100))
        at_threshold = Observation(1, self.start, "pothole", 0.8, (0, 35, 20, 55), crop,
                                   (100, 100))
        track = TrackSummary(3, [above])
        with tempfile.TemporaryDirectory() as directory:
            with patch("spm_capture.offline._save_crop", return_value=True):
                rejected = track.to_record(1, Path(directory), [], severity_config=config)
                track.observations = [above, at_threshold]
                record = track.to_record(1, Path(directory), [], severity_config=config)

        self.assertIsNone(rejected)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["frame_key"], 1)
        self.assertEqual(record["frames_detected"], 1)

    def test_severity_thresholds_are_deterministic(self) -> None:
        config = SeverityConfig(light_area_threshold=0.01, critical_area_threshold=0.05)
        self.assertEqual(config.severity_for(0.009), "leve")
        self.assertEqual(config.severity_for(0.01), "moderado")
        self.assertEqual(config.severity_for(0.05), "critico")

    def test_perspective_factor_is_one_at_reference_and_increases_toward_horizon(self) -> None:
        config = SeverityConfig()
        self.assertAlmostEqual(config.area_factor(70, 100), 1.0)
        self.assertGreater(config.area_factor(50, 100), 1.0)

    def test_reads_recording_frame_index_csvs_when_present(self) -> None:
        index_root = Path(__file__).parents[1] / "record_tests" / "recording_frames"
        index_files = sorted(index_root.glob("*/frames_index.csv"))
        if not index_files:
            self.skipTest("No hay índices de frames locales en record_tests.")

        for index_file in index_files:
            with self.subTest(session=index_file.parent.name):
                timestamps = load_frame_timestamps(index_file)
                self.assertTrue(timestamps)
                self.assertTrue(all(timestamp.tzinfo is not None for timestamp in timestamps.values()))

    def test_loads_utc_timestamps_indexed_by_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "frames.csv"
            csv_path.write_text(
                "frame,t_rel_s,epoch_s,utc\n0,0,1,2026-10-26T12:00:00.000+00:00\n",
                encoding="utf-8",
            )
            timestamps = load_frame_timestamps(csv_path)

        self.assertEqual(timestamps[0], self.start)

    def test_process_session_exports_a_georeferenced_track_and_crop(self) -> None:
        class FakeFrame:
            shape = (10, 10, 3)
            size = 300

            def __getitem__(self, _key: object) -> FakeFrame:
                return self

            def copy(self) -> FakeFrame:
                return self

        class FakeCapture:
            def __init__(self) -> None:
                self.frame_index = 0
                self.released = False

            def isOpened(self) -> bool:
                return True

            def get(self, _property: int) -> float:
                return 30.0

            def read(self) -> tuple[bool, FakeFrame | None]:
                if self.frame_index >= 2:
                    return False, None
                self.frame_index += 1
                return True, FakeFrame()

            def release(self) -> None:
                self.released = True

        class FakeTensor:
            def __init__(self, values: list[object]) -> None:
                self.values = values

            def int(self) -> FakeTensor:
                return self

            def tolist(self) -> list[object]:
                return self.values

        capture = FakeCapture()
        fake_cv2 = ModuleType("cv2")
        fake_cv2.CAP_PROP_FPS = 5
        fake_cv2.VideoCapture = lambda _path: capture
        fake_cv2.rectangle = lambda *_args, **_kwargs: None

        def write_crop(path: str, _crop: FakeFrame) -> bool:
            Path(path).write_bytes(b"crop")
            return True

        fake_cv2.imwrite = write_crop

        class FakeModel:
            names = {0: "pothole"}

            def __init__(self, _model_path: str) -> None:
                self.calls = 0

            def track(self, _frame: FakeFrame, **kwargs: object) -> list[object]:
                self.assert_tracking_options(kwargs)
                self.calls += 1
                boxes = SimpleNamespace(
                    id=FakeTensor([9]),
                    cls=FakeTensor([0]),
                    conf=FakeTensor([0.6 if self.calls == 1 else 0.9]),
                    xyxy=FakeTensor([[1.0, 1.0, 5.0, 5.0]]),
                )
                return [SimpleNamespace(boxes=boxes)]

            @staticmethod
            def assert_tracking_options(options: dict[str, object]) -> None:
                assert options["persist"] is True
                assert options["tracker"] == "bytetrack.yaml"
                assert options["classes"] == [0]

        fake_ultralytics = ModuleType("ultralytics")
        fake_ultralytics.YOLO = FakeModel
        points = [
            SimpleNamespace(time=self.start, latitude=-27.0, longitude=-55.0),
            SimpleNamespace(time=self.start + timedelta(seconds=10), latitude=-26.0, longitude=-54.0),
        ]
        fake_gpxpy = ModuleType("gpxpy")
        fake_gpxpy.parse = lambda _source: SimpleNamespace(
            tracks=[SimpleNamespace(segments=[SimpleNamespace(points=points)])]
        )

        with tempfile.TemporaryDirectory() as directory:
            session_dir = Path(directory)
            (session_dir / "video.mp4").touch()
            (session_dir / "best.pt").touch()
            (session_dir / "route.gpx").touch()
            (session_dir / "frames.csv").write_text(
                "frame,t_rel_s,epoch_s,utc\n"
                "0,0,1,2026-10-26T12:00:00+00:00\n"
                "1,2,3,2026-10-26T12:00:02+00:00\n",
                encoding="utf-8",
            )
            with patch.dict("sys.modules", {"cv2": fake_cv2, "ultralytics": fake_ultralytics,
                                            "gpxpy": fake_gpxpy}):
                output_path = process_session(
                    session_dir, session_dir / "best.pt", min_frames=2,
                    severity_config=SeverityConfig(roi_horizon_ratio=0.0),
                )

            import json

            records = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(capture.released)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["severity"], "critico")
            self.assertIn("area_norm", records[0])
            self.assertEqual(records[0]["frame_key"], 1)
            self.assertEqual(records[0]["latitude"], -26.8)
            self.assertEqual(records[0]["longitude"], -54.8)
            self.assertEqual(records[0]["location_method"], "gps_vehicle")
            self.assertTrue((session_dir / records[0]["evidence_image"]).is_file())

            # Con camera_calibration.json en la sesión, la posición se proyecta hacia adelante.
            (session_dir / "camera_calibration.json").write_text(
                json.dumps({"camera_height_m": 1.5, "pitch_deg": 60.0, "hfov_deg": 90.0}),
                encoding="utf-8",
            )
            capture.frame_index = 0
            with patch.dict("sys.modules", {"cv2": fake_cv2, "ultralytics": fake_ultralytics,
                                            "gpxpy": fake_gpxpy}):
                process_session(
                    session_dir, session_dir / "best.pt", min_frames=2,
                    severity_config=SeverityConfig(roi_horizon_ratio=0.0),
                )
            projected = json.loads(output_path.read_text(encoding="utf-8"))[0]
            self.assertEqual(projected["location_method"], "camera_projection")
            self.assertEqual(projected["vehicle_latitude"], -26.8)
            # La geolocalización calibrada corresponde al mismo keyframe que el registro.
            self.assertEqual(projected["projected_samples"], 1)
            self.assertGreater(projected["latitude"], -26.9)
            self.assertGreater(projected["longitude"], -54.9)

            with patch.dict("sys.modules", {"cv2": fake_cv2, "ultralytics": fake_ultralytics,
                                            "gpxpy": fake_gpxpy}):
                capture.frame_index = 0
                process_session(session_dir, session_dir / "best.pt", min_frames=2,
                                use_calibration=False,
                                severity_config=SeverityConfig(roi_horizon_ratio=0.0))
            raw = json.loads(output_path.read_text(encoding="utf-8"))[0]
            self.assertEqual(raw["location_method"], "gps_vehicle")


if __name__ == "__main__":
    unittest.main()