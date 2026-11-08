from __future__ import annotations

import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spm_capture.geometry import (
    CameraCalibration,
    load_calibration,
    local_offset_m,
    offset_position,
    solve_pitch,
    solve_pitch_and_fov,
)
from spm_capture.offline import GPSPoint, Observation, estimate_heading, locate_track

WIDTH, HEIGHT = 1920, 1080
START = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
METERS_PER_DEG_LAT = math.radians(1) * 6_371_008.8


def row_for_distance(distance: float, height: float, pitch_deg: float, hfov_deg: float) -> float:
    focal = (WIDTH / 2) / math.tan(math.radians(hfov_deg) / 2)
    angle = math.atan2(height, distance) - math.radians(pitch_deg)
    return HEIGHT / 2 + focal * math.tan(angle)


def northbound_track(speed_mps: float = 10.0, seconds: int = 10) -> list[GPSPoint]:
    """Vehículo hacia el norte a velocidad constante desde (-27, -55)."""
    return [
        GPSPoint(START + timedelta(seconds=s), -27.0 + s * speed_mps / METERS_PER_DEG_LAT, -55.0)
        for s in range(seconds + 1)
    ]


class CameraCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = CameraCalibration(camera_height_m=1.5, pitch_deg=10.0, hfov_deg=90.0)

    def test_center_pixel_hits_the_ground_along_the_optical_axis(self) -> None:
        forward, right, distance = self.calibration.project_pixel(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
        expected = 1.5 / math.tan(math.radians(10.0))
        self.assertAlmostEqual(forward, expected, places=6)
        self.assertAlmostEqual(right, 0.0, places=6)
        self.assertAlmostEqual(distance, expected, places=6)

    def test_pixel_right_of_center_projects_to_the_right(self) -> None:
        forward, right, _ = self.calibration.project_pixel(WIDTH * 0.75, HEIGHT * 0.8, WIDTH, HEIGHT)
        self.assertGreater(forward, 0)
        self.assertGreater(right, 0)

    def test_mount_offsets_and_yaw_are_applied(self) -> None:
        calibration = CameraCalibration(1.5, 10.0, 90.0, forward_offset_m=1.0, right_offset_m=-0.5)
        forward, right, distance = calibration.project_pixel(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
        self.assertAlmostEqual(forward, distance + 1.0, places=6)
        self.assertAlmostEqual(right, -0.5, places=6)

        turned = CameraCalibration(1.5, 10.0, 90.0, yaw_deg=30.0)
        forward, right, distance = turned.project_pixel(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT)
        self.assertAlmostEqual(math.degrees(math.atan2(right, forward)), 30.0, places=6)
        self.assertAlmostEqual(math.hypot(forward, right), distance, places=6)

    def test_rejects_pixels_above_horizon_or_beyond_max_distance(self) -> None:
        self.assertIsNone(self.calibration.project_pixel(WIDTH / 2, 0, WIDTH, HEIGHT))
        near_horizon = row_for_distance(40.0, 1.5, 10.0, 90.0)
        self.assertIsNone(self.calibration.project_pixel(WIDTH / 2, near_horizon, WIDTH, HEIGHT))

    def test_validates_values_and_round_trips_json(self) -> None:
        with self.assertRaises(ValueError):
            CameraCalibration(camera_height_m=0, pitch_deg=10, hfov_deg=90)
        with self.assertRaises(ValueError):
            CameraCalibration.from_dict({"camera_height_m": 1.5, "pitch_deg": 10})
        with self.assertRaises(ValueError):
            CameraCalibration.from_dict({"camera_height_m": 1.5, "pitch_deg": "x", "hfov_deg": 90})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "camera_calibration.json"
            self.calibration.save(path)
            self.assertEqual(CameraCalibration.load(path), self.calibration)
            self.assertIsNone(load_calibration(Path(directory) / "missing.json", required=False))
            with self.assertRaises(FileNotFoundError):
                load_calibration(Path(directory) / "missing.json")
            path.write_text(json.dumps({**self.calibration.to_dict(), "nota": "x"}), encoding="utf-8")
            self.assertEqual(CameraCalibration.load(path), self.calibration)


class SolverTests(unittest.TestCase):
    def test_recovers_pitch_from_ground_markers(self) -> None:
        markers = [(d, row_for_distance(d, 1.35, 12.0, 78.0)) for d in (5.0, 10.0, 15.0)]
        pitch, residuals = solve_pitch(markers, 1.35, WIDTH, HEIGHT, 78.0)
        self.assertAlmostEqual(pitch, 12.0, places=6)
        self.assertTrue(all(abs(value) < 1e-6 for value in residuals))

    def test_recovers_pitch_and_fov_from_several_markers(self) -> None:
        markers = [(d, row_for_distance(d, 1.35, 12.0, 78.0)) for d in (4.0, 8.0, 15.0)]
        pitch, hfov, residuals = solve_pitch_and_fov(markers, 1.35, WIDTH, HEIGHT)
        self.assertAlmostEqual(hfov, 78.0, delta=0.1)
        self.assertAlmostEqual(pitch, 12.0, delta=0.05)
        self.assertTrue(all(abs(value) < 0.05 for value in residuals))

    def test_fov_needs_two_distinct_rows(self) -> None:
        with self.assertRaises(ValueError):
            solve_pitch_and_fov([(5.0, 800.0)], 1.35, WIDTH, HEIGHT)


class PositionTests(unittest.TestCase):
    def test_offset_position_moves_along_heading(self) -> None:
        latitude, longitude = offset_position(-27.0, -55.0, 90.0, 10.0, 0.0)
        north, east = local_offset_m(-27.0, -55.0, latitude, longitude)
        self.assertAlmostEqual(north, 0.0, places=4)
        self.assertAlmostEqual(east, 10.0, places=4)

        latitude, longitude = offset_position(-27.0, -55.0, 0.0, 0.0, 3.0)
        north, east = local_offset_m(-27.0, -55.0, latitude, longitude)
        self.assertAlmostEqual(east, 3.0, places=4)

    def test_estimates_heading_and_ignores_stationary_vehicle(self) -> None:
        heading = estimate_heading(START + timedelta(seconds=5), northbound_track())
        self.assertIsNotNone(heading)
        assert heading is not None
        self.assertAlmostEqual(min(heading, 360 - heading), 0.0, places=6)

        eastbound = [GPSPoint(START + timedelta(seconds=s), -27.0, -55.0 + s * 1e-4) for s in range(5)]
        self.assertAlmostEqual(estimate_heading(START, eastbound), 90.0, places=3)

        parked = [GPSPoint(START + timedelta(seconds=s), -27.0, -55.0) for s in range(20)]
        self.assertIsNone(estimate_heading(START + timedelta(seconds=10), parked))


class LocateTrackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = CameraCalibration(camera_height_m=1.5, pitch_deg=10.0, hfov_deg=90.0,
                                             forward_offset_m=1.0)
        self.track = northbound_track()

    def observation(self, second: float, distance: float, box_height: int = 40) -> Observation:
        row = row_for_distance(distance, 1.5, 10.0, 90.0)
        top = int(round(row)) - box_height // 2
        box = (WIDTH // 2 - 50, top, WIDTH // 2 + 50, top + box_height)
        return Observation(0, START + timedelta(seconds=second), "pothole_light", 0.9, box,
                           SimpleNamespace(size=1), (WIDTH, HEIGHT))

    def test_projects_pothole_ahead_of_the_gps_antenna(self) -> None:
        # Bache fijo a 50 m al norte del inicio: el vehículo avanza 10 m/s.
        observations = [self.observation(s, 50.0 - 10.0 * s - 1.0) for s in (2.0, 3.0, 3.5)]
        location = locate_track(observations, observations[0], self.track, self.calibration)

        self.assertEqual(location["location_method"], "camera_projection")
        self.assertEqual(location["projected_samples"], 1)
        north, east = local_offset_m(-27.0, -55.0, location["latitude"], location["longitude"])
        self.assertAlmostEqual(north, 50.0, delta=0.3)
        self.assertAlmostEqual(east, 0.0, delta=0.05)
        vehicle_north, _ = local_offset_m(-27.0, -55.0, location["vehicle_latitude"],
                                          location["vehicle_longitude"])
        self.assertAlmostEqual(vehicle_north, 20.0, delta=0.01)

    def test_calibrated_location_projects_only_the_selected_keyframe(self) -> None:
        observations = [self.observation(2.0, 20.0), self.observation(3.0, 10.0)]
        best = observations[1]
        with patch("spm_capture.offline.CameraCalibration.project_pixel",
                   return_value=(12.0, 0.0, 12.0)) as project_pixel, \
             patch("spm_capture.offline.estimate_heading", return_value=0.0), \
             patch("spm_capture.offline.offset_position", return_value=(-26.9, -54.9)):
            location = locate_track(observations, best, self.track, self.calibration)

        project_pixel.assert_called_once_with(
            (best.box[0] + best.box[2]) / 2,
            (best.box[1] + best.box[3]) / 2,
            WIDTH,
            HEIGHT,
        )
        self.assertEqual(location["projected_samples"], 1)
        self.assertEqual((location["latitude"], location["longitude"]), (-26.9, -54.9))

    def test_time_offset_shifts_gps_lookup(self) -> None:
        calibration = CameraCalibration(1.5, 10.0, 90.0, time_offset_s=1.0)
        observations = [self.observation(2.0, 10.0)]
        location = locate_track(observations, observations[0], self.track, calibration)
        vehicle_north, _ = local_offset_m(-27.0, -55.0, location["vehicle_latitude"],
                                          location["vehicle_longitude"])
        self.assertAlmostEqual(vehicle_north, 30.0, delta=0.01)

    def test_falls_back_to_gps_without_calibration_or_heading(self) -> None:
        observations = [self.observation(2.0, 10.0)]
        raw = locate_track(observations, observations[0], self.track, None)
        self.assertEqual(raw["location_method"], "gps_vehicle")
        self.assertEqual(raw["latitude"], raw["vehicle_latitude"])

        parked = [GPSPoint(START + timedelta(seconds=s), -27.0, -55.0) for s in range(10)]
        stopped = locate_track(observations, observations[0], parked, self.calibration)
        self.assertEqual(stopped["location_method"], "gps_vehicle")
        self.assertEqual((stopped["latitude"], stopped["longitude"]), (-27.0, -55.0))

    def test_prefers_boxes_not_clipped_by_the_frame(self) -> None:
        clean = self.observation(3.0, 19.0)
        clipped = Observation(0, START + timedelta(seconds=3.5), "pothole_light", 0.9,
                              (900, 1000, 1020, HEIGHT), SimpleNamespace(size=1), (WIDTH, HEIGHT))
        location = locate_track([clean, clipped], clean, self.track, self.calibration)
        self.assertEqual(location["projected_samples"], 1)
        north, _ = local_offset_m(-27.0, -55.0, location["latitude"], location["longitude"])
        self.assertAlmostEqual(north, 50.0, delta=0.3)


if __name__ == "__main__":
    unittest.main()
