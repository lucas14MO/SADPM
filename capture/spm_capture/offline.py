"""Procesamiento offline de sesiones de video y georreferenciacion GPX."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

from .geometry import (
    CALIBRATION_FILENAME,
    CameraCalibration,
    local_offset_m,
    offset_position,
)

SEVERITY_CLASSES = ("pothole_light", "pothole_moderate", "pothole_critical")


@dataclass(frozen=True)
class GPSPoint:
    timestamp: datetime
    latitude: float
    longitude: float


@dataclass
class Observation:
    frame: int
    timestamp: datetime
    label: str
    confidence: float
    box: tuple[int, int, int, int]
    crop: Any = field(repr=False)
    frame_size: tuple[int, int] | None = None  # (ancho, alto) del fotograma


@dataclass
class TrackSummary:
    track_id: int
    observations: list[Observation] = field(default_factory=list)

    def to_record(self, min_frames: int, output_dir: Path,
                  gpx_data: Sequence[GPSPoint],
                  calibration: CameraCalibration | None = None) -> dict[str, Any] | None:
        if len(self.observations) < min_frames:
            return None

        votes = Counter(item.label for item in self.observations)
        confidence_by_class: dict[str, float] = defaultdict(float)
        for item in self.observations:
            confidence_by_class[item.label] += item.confidence
        class_index = {name: index for index, name in enumerate(SEVERITY_CLASSES)}
        label = min(
            votes,
            key=lambda name: (-votes[name], -confidence_by_class[name], class_index[name]),
        )
        best = max(self.observations, key=lambda item: item.confidence)
        location = locate_track(self.observations, best, gpx_data, calibration)
        crop_dir = output_dir / "crops"
        crop_dir.mkdir(parents=True, exist_ok=True)
        crop_path = crop_dir / f"pothole_{self.track_id:04d}.jpg"
        if best.crop is None or best.crop.size == 0 or not _save_crop(crop_path, best.crop):
            raise OSError(f"No se pudo guardar la evidencia: {crop_path}")

        return {
            "track_id": self.track_id,
            "severity": label,
            "confidence_avg": round(
                sum(item.confidence for item in self.observations) / len(self.observations), 6
            ),
            "confidence_max": round(best.confidence, 6),
            **location,
            "timestamp": best.timestamp.isoformat(timespec="milliseconds"),
            "frame_key": best.frame,
            "frames_detected": len(self.observations),
            "evidence_image": crop_path.relative_to(output_dir).as_posix(),
        }


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Los timestamps deben incluir zona horaria.")
    return value.astimezone(timezone.utc)


def interpolate_gps_position(
    timestamp: datetime,
    gpx_data: Sequence[GPSPoint],
) -> tuple[float, float] | tuple[None, None]:
    """Interpola latitud/longitud; devuelve None fuera de la cobertura GPS."""
    target = _utc_datetime(timestamp)
    points = sorted(gpx_data, key=lambda point: _utc_datetime(point.timestamp))
    if not points:
        return None, None

    previous: GPSPoint | None = None
    for current in points:
        current_time = _utc_datetime(current.timestamp)
        if current_time == target:
            return current.latitude, current.longitude
        if current_time > target:
            if previous is None:
                return None, None
            previous_time = _utc_datetime(previous.timestamp)
            elapsed = (target - previous_time).total_seconds()
            interval = (current_time - previous_time).total_seconds()
            if interval <= 0:
                return previous.latitude, previous.longitude
            fraction = elapsed / interval
            return (
                previous.latitude + fraction * (current.latitude - previous.latitude),
                previous.longitude + fraction * (current.longitude - previous.longitude),
            )
        previous = current
    return None, None


def estimate_heading(
    timestamp: datetime,
    gpx_data: Sequence[GPSPoint],
    window_s: float = 1.0,
    min_displacement_m: float = 2.0,
    max_window_s: float = 8.0,
) -> float | None:
    """Rumbo del vehículo (grados desde el norte, sentido horario) en ``timestamp``.

    Compara las posiciones interpoladas en ``t - ventana`` y ``t + ventana``; si
    el vehículo se movió menos de ``min_displacement_m`` (detenido o ruido GPS)
    duplica la ventana hasta ``max_window_s``. Devuelve ``None`` si no hay
    desplazamiento suficiente para un rumbo fiable.
    """
    here = interpolate_gps_position(timestamp, gpx_data)
    window = window_s
    while window <= max_window_s:
        delta = timedelta(seconds=window)
        before = interpolate_gps_position(timestamp - delta, gpx_data)
        after = interpolate_gps_position(timestamp + delta, gpx_data)
        before = here if before[0] is None else before
        after = here if after[0] is None else after
        if before[0] is not None and after[0] is not None:
            north, east = local_offset_m(before[0], before[1], after[0], after[1])
            if math.hypot(north, east) >= min_displacement_m:
                return math.degrees(math.atan2(east, north)) % 360
        window *= 2
    return None


def _touches_border(box: tuple[int, int, int, int], width: int, height: int, margin: int = 2) -> bool:
    x1, y1, x2, y2 = box
    return x1 <= margin or y1 <= margin or x2 >= width - margin or y2 >= height - margin


def locate_track(
    observations: Sequence[Observation],
    best: Observation,
    gpx_data: Sequence[GPSPoint],
    calibration: CameraCalibration | None,
) -> dict[str, Any]:
    """Ubica el bache de un track.

    Sin calibración, la posición es la del GPS (antena) en el mejor fotograma,
    como antes. Con calibración, cada observación se proyecta sobre la calzada
    y se desplaza desde la posición del vehículo según su rumbo; el resultado es
    el promedio ponderado por ``1 / (h² + d²)``, porque el error de la proyección
    crece con el cuadrado de la distancia. Se prefieren las cajas que no tocan el
    borde de la imagen (un bache cortado desplaza el centro de la caja).
    """
    offset = timedelta(seconds=calibration.time_offset_s if calibration else 0.0)
    vehicle_latitude, vehicle_longitude = interpolate_gps_position(best.timestamp + offset, gpx_data)
    location: dict[str, Any] = {
        "latitude": vehicle_latitude,
        "longitude": vehicle_longitude,
        "location_method": "gps_vehicle",
        "vehicle_latitude": vehicle_latitude,
        "vehicle_longitude": vehicle_longitude,
        "projected_samples": 0,
    }
    if calibration is None:
        return location

    clean: list[tuple[float, float, float]] = []
    clipped: list[tuple[float, float, float]] = []
    for item in observations:
        if item.frame_size is None:
            continue
        width, height = item.frame_size
        x1, y1, x2, y2 = item.box
        projection = calibration.project_pixel((x1 + x2) / 2, (y1 + y2) / 2, width, height)
        if projection is None:
            continue
        moment = item.timestamp + offset
        latitude, longitude = interpolate_gps_position(moment, gpx_data)
        if latitude is None or longitude is None:
            continue
        heading = estimate_heading(moment, gpx_data)
        if heading is None:
            continue
        forward, right, distance = projection
        point = offset_position(latitude, longitude, heading, forward, right)
        weight = 1.0 / (calibration.camera_height_m ** 2 + distance ** 2)
        target = clipped if _touches_border(item.box, width, height) else clean
        target.append((point[0], point[1], weight))

    samples = clean or clipped
    if not samples:
        return location
    total = sum(weight for _, _, weight in samples)
    location.update(
        latitude=round(sum(lat * weight for lat, _, weight in samples) / total, 8),
        longitude=round(sum(lon * weight for _, lon, weight in samples) / total, 8),
        location_method="camera_projection",
        projected_samples=len(samples),
    )
    return location


def load_gpx(path: Path) -> list[GPSPoint]:
    """Lee puntos GPX con timestamp; ignora puntos sin hora o coordenadas invalidas."""
    try:
        import gpxpy
    except ImportError as exc:
        raise RuntimeError("Falta gpxpy. Instala las dependencias de capture/.") from exc

    with path.open("r", encoding="utf-8") as source:
        gpx = gpxpy.parse(source)
    points: list[GPSPoint] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point.time is None:
                    continue
                timestamp = _utc_datetime(point.time)
                if not (math.isfinite(point.latitude) and math.isfinite(point.longitude)):
                    continue
                points.append(GPSPoint(timestamp, point.latitude, point.longitude))
    points.sort(key=lambda point: point.timestamp)
    return points


def load_frame_timestamps(path: Path) -> dict[int, datetime]:
    timestamps: dict[int, datetime] = {}
    with path.open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if not {"frame", "utc"}.issubset(reader.fieldnames or ()):
            raise ValueError("frames.csv debe contener las columnas 'frame' y 'utc'.")
        for row in reader:
            frame = int(row["frame"])
            timestamp = _utc_datetime(datetime.fromisoformat(row["utc"]))
            if frame in timestamps:
                raise ValueError(f"Índice de frame duplicado en frames.csv: {frame}")
            timestamps[frame] = timestamp
    if not timestamps:
        raise ValueError("frames.csv no contiene timestamps.")
    return timestamps


def _crop(frame: Any, box: tuple[int, int, int, int], margin: float = 0.15) -> Any:
    x1, y1, x2, y2 = box
    height, width = frame.shape[:2]
    margin_x, margin_y = int((x2 - x1) * margin), int((y2 - y1) * margin)
    return frame[max(0, y1 - margin_y):min(height, y2 + margin_y),
                 max(0, x1 - margin_x):min(width, x2 + margin_x)].copy()


def _save_crop(path: Path, crop: Any) -> bool:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Falta opencv-python. Instala las dependencias de capture/.") from exc

    return bool(cv2.imwrite(str(path), crop))


def process_session(
    session_dir: Path,
    model_path: Path,
    gpx_path: Path | None = None,
    confidence: float = 0.3,
    image_size: int = 640,
    min_frames: int = 3,
    tracker: str = "bytetrack.yaml",
    calibration_path: Path | None = None,
    use_calibration: bool = True,
) -> Path:
    """Ejecuta tracking persistente sobre el video y exporta los baches unicos.

    La calibración de cámara se toma de ``calibration_path`` o, si no se indica,
    de ``camera_calibration.json`` dentro de la sesión. Sin calibración (o con
    ``use_calibration=False``) se exporta la posición del GPS sin corregir.
    """
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("Falta opencv-python. Instala las dependencias de capture/.") from exc

    session_dir, model_path = Path(session_dir), Path(model_path)
    video_path = session_dir / "video.mp4"
    frames_path = session_dir / "frames.csv"
    if not session_dir.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de sesión: {session_dir}")
    for required in (video_path, frames_path, model_path):
        if not required.is_file():
            raise FileNotFoundError(f"No existe el archivo requerido: {required}")
    if not 0 < confidence <= 1:
        raise ValueError("confidence debe estar en el intervalo (0, 1].")
    if image_size <= 0 or min_frames <= 0:
        raise ValueError("image_size y min_frames deben ser mayores que cero.")

    if gpx_path is None:
        candidates = sorted(session_dir.glob("*.gpx"))
        if len(candidates) != 1:
            raise ValueError("Indica --gpx si la sesión no contiene exactamente un archivo GPX.")
        gpx_path = candidates[0]
    elif not Path(gpx_path).is_file():
        raise FileNotFoundError(f"No existe el archivo GPX: {gpx_path}")

    calibration: CameraCalibration | None = None
    if use_calibration:
        if calibration_path is None:
            default_path = session_dir / CALIBRATION_FILENAME
            calibration_path = default_path if default_path.is_file() else None
        elif not Path(calibration_path).is_file():
            raise FileNotFoundError(f"No existe el archivo de calibración: {calibration_path}")
        if calibration_path is not None:
            calibration = CameraCalibration.load(Path(calibration_path))

    timestamps = load_frame_timestamps(frames_path)
    gpx_data = load_gpx(Path(gpx_path))
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Falta ultralytics. Instala las dependencias de capture/.") from exc

    model = YOLO(str(model_path))
    names = model.names
    name_by_id = {int(key): str(value) for key, value in names.items()} if isinstance(names, dict) else dict(enumerate(names))
    class_ids = [class_id for class_id, name in name_by_id.items() if name in SEVERITY_CLASSES]
    if len(class_ids) != len(SEVERITY_CLASSES):
        raise ValueError(f"El modelo debe tener estas clases: {', '.join(SEVERITY_CLASSES)}")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise OSError(f"No se pudo abrir el video: {video_path}")

    tracks: dict[int, TrackSummary] = {}
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not math.isfinite(fps) or fps <= 0:
        capture.release()
        raise ValueError(f"FPS inválidos en el video: {fps}")
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index not in timestamps:
                raise ValueError(f"frames.csv no contiene el frame {frame_index} del video.")
            result = model.track(
                frame,
                persist=True,
                tracker=tracker,
                conf=confidence,
                imgsz=image_size,
                classes=class_ids,
                verbose=False,
            )[0]
            boxes = result.boxes
            if boxes is not None and boxes.id is not None:
                ids = boxes.id.int().tolist()
                classes = boxes.cls.int().tolist()
                confidences = boxes.conf.tolist()
                coordinates = boxes.xyxy.tolist()
                for track_id, class_id, score, raw_box in zip(ids, classes, confidences, coordinates):
                    label = name_by_id[class_id]
                    if label not in SEVERITY_CLASSES:
                        continue
                    height, width = frame.shape[:2]
                    x1, y1, x2, y2 = (int(round(value)) for value in raw_box)
                    box = (max(0, x1), max(0, y1), min(width, x2), min(height, y2))
                    observation = Observation(
                        frame_index,
                        timestamps[frame_index],
                        label,
                        float(score),
                        box,
                        _crop(frame, box),
                        (width, height),
                    )
                    tracks.setdefault(track_id, TrackSummary(track_id)).observations.append(observation)
            frame_index += 1
    finally:
        capture.release()

    records = [
        record
        for track_id in sorted(tracks)
        if (record := tracks[track_id].to_record(min_frames, session_dir, gpx_data, calibration))
        is not None
    ]
    output_path = session_dir / "processed_potholes.json"
    temporary_path = output_path.with_suffix(".json.tmp")
    with temporary_path.open("w", encoding="utf-8") as output:
        json.dump(records, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")
    temporary_path.replace(output_path)
    print(f"Video: {video_path.name} | FPS: {fps:.3f} | Frames: {frame_index}")
    print(f"Baches exportados: {len(records)} -> {output_path}")
    if calibration is None:
        print("Sin calibración de cámara: las coordenadas son las del GPS, sin offset.")
    else:
        projected = sum(record["location_method"] == "camera_projection" for record in records)
        print(f"Calibración {calibration_path}: {projected}/{len(records)} baches con "
              f"posición proyectada; el resto usa la posición del GPS.")
    return output_path