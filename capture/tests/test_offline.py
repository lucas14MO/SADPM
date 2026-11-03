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

    def test_track_votes_by_majority_and_uses_highest_confidence_frame(self) -> None:
        track = TrackSummary(7)
        crop = SimpleNamespace(size=1)
        track.observations = [
            Observation(2, self.start, "pothole_light", 0.9, (0, 0, 2, 2), crop),
            Observation(4, self.start + timedelta(seconds=2), "pothole_moderate", 0.7, (0, 0, 2, 2), crop),
            Observation(5, self.start + timedelta(seconds=3), "pothole_moderate", 0.8, (0, 0, 2, 2), crop),
        ]
        with tempfile.TemporaryDirectory() as directory:
            with patch("spm_capture.offline._save_crop", return_value=True):
                record = track.to_record(3, Path(directory), [])

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["severity"], "pothole_moderate")
        self.assertEqual(record["frame_key"], 2)
        self.assertEqual(record["confidence_max"], 0.9)
        self.assertAlmostEqual(record["confidence_avg"], 0.8)
        self.assertEqual(record["latitude"], None)

    def test_track_tie_breaks_by_total_class_confidence(self) -> None:
        track = TrackSummary(3)
        crop = SimpleNamespace(size=1)
        track.observations = [
            Observation(0, self.start, "pothole_light", 0.5, (0, 0, 2, 2), crop),
            Observation(1, self.start, "pothole_critical", 0.8, (0, 0, 2, 2), crop),
        ]
        with tempfile.TemporaryDirectory() as directory:
            with patch("spm_capture.offline._save_crop", return_value=True):
                record = track.to_record(1, Path(directory), [])

        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["severity"], "pothole_critical")

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

        def write_crop(path: str, _crop: FakeFrame) -> bool:
            Path(path).write_bytes(b"crop")
            return True

        fake_cv2.imwrite = write_crop

        class FakeModel:
            names = {0: "pothole_light", 1: "pothole_moderate", 2: "pothole_critical"}

            def __init__(self, _model_path: str) -> None:
                self.calls = 0

            def track(self, _frame: FakeFrame, **kwargs: object) -> list[object]:
                self.assert_tracking_options(kwargs)
                self.calls += 1
                class_id = self.calls - 1
                boxes = SimpleNamespace(
                    id=FakeTensor([9]),
                    cls=FakeTensor([class_id]),
                    conf=FakeTensor([[0.6], [0.9]][class_id]),
                    xyxy=FakeTensor([[1.0, 1.0, 5.0, 5.0]]),
                )
                return [SimpleNamespace(boxes=boxes)]

            @staticmethod
            def assert_tracking_options(options: dict[str, object]) -> None:
                assert options["persist"] is True
                assert options["tracker"] == "bytetrack.yaml"

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
                output_path = process_session(session_dir, session_dir / "best.pt", min_frames=2)

            import json

            records = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(capture.released)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["severity"], "pothole_moderate")
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
                process_session(session_dir, session_dir / "best.pt", min_frames=2)
            projected = json.loads(output_path.read_text(encoding="utf-8"))[0]
            self.assertEqual(projected["location_method"], "camera_projection")
            self.assertEqual(projected["vehicle_latitude"], -26.8)
            # Se promedian las dos observaciones (vehículo en -27/-55 y -26.8/-54.8); como
            # avanza hacia el noreste, el bache queda delante del punto medio de la antena.
            self.assertEqual(projected["projected_samples"], 2)
            self.assertGreater(projected["latitude"], -26.9)
            self.assertGreater(projected["longitude"], -54.9)

            with patch.dict("sys.modules", {"cv2": fake_cv2, "ultralytics": fake_ultralytics,
                                            "gpxpy": fake_gpxpy}):
                capture.frame_index = 0
                process_session(session_dir, session_dir / "best.pt", min_frames=2,
                                use_calibration=False)
            raw = json.loads(output_path.read_text(encoding="utf-8"))[0]
            self.assertEqual(raw["location_method"], "gps_vehicle")


if __name__ == "__main__":
    unittest.main()