"""Detección y seguimiento (tracking) de baches en vivo.

``PotholeTracker`` envuelve un modelo YOLO de Ultralytics con ByteTrack y
asigna un ID estable a cada bache mientras permanece en el campo de visión.
``DetectionLog`` guarda los registros de una sesión de grabación:

- ``annotated.mp4``   — video con las cajas e IDs dibujados.
- ``detections.csv``  — una fila por bache y fotograma (ID, confianza, caja).
- ``tracks.csv``      — una fila por bache único (primer/último fotograma y
  hora UTC, confianza máxima, recorte de evidencia).
- ``crops/``          — recorte del mejor fotograma de cada bache.
"""

from __future__ import annotations

import csv
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import cv2

from .recorder import AsyncVideoWriter

# Modelo propio V4 (YOLO26 Small, clase única ``pothole``), el mismo que usa el
# procesamiento offline (``process_video.py``). Ver weights/IA_Models.md.
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "weights" / "weights_v4_monoclass.pt"
)

# Etiquetas mostradas en pantalla (sin tildes: las fuentes de OpenCV no las soportan).
LABELS = {"pothole": "Bache", "sewage-manhole": "Tapa"}

PALETTE = [
    (56, 56, 255), (31, 112, 255), (29, 178, 255), (49, 210, 207), (10, 249, 72),
    (23, 204, 146), (134, 219, 61), (187, 212, 0), (255, 194, 0), (255, 115, 100),
    (236, 24, 0), (255, 56, 132), (133, 0, 82), (255, 56, 203), (200, 149, 255),
]


def ensure_model(path: Path = DEFAULT_MODEL_PATH) -> Path:
    """Verifica que existan los pesos del modelo."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el modelo {path}")
    return path


@dataclass
class Detection:
    track_id: int
    label: str
    conf: float
    box: tuple[int, int, int, int]  # x1, y1, x2, y2 en píxeles del fotograma

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) // 2, (y1 + y2) // 2


class PotholeTracker:
    def __init__(
        self,
        model_path: Path,
        conf: float = 0.3,
        imgsz: int = 640,
        classes: list[int] | None = None,
        tracker: str = "bytetrack.yaml",
        trail: int = 30,
    ) -> None:
        from ultralytics import YOLO  # import diferido: tarda varios segundos

        self.model = YOLO(str(model_path))
        self.conf, self.imgsz, self.classes, self.tracker = conf, imgsz, classes, tracker
        self.names = self.model.names
        self._ids: dict[int, int] = {}  # ID interno del tracker -> ID consecutivo
        self.trails: dict[int, deque] = {}
        self._trail = trail

    def update(self, frame) -> list[Detection]:
        result = self.model.track(
            frame,
            persist=True,
            tracker=self.tracker,
            conf=self.conf,
            imgsz=self.imgsz,
            classes=self.classes,
            verbose=False,
        )[0]
        boxes = result.boxes
        if boxes is None or boxes.id is None:
            return []

        detections = []
        h, w = frame.shape[:2]
        for raw_id, cls, conf, xyxy in zip(
            boxes.id.int().tolist(), boxes.cls.int().tolist(), boxes.conf.tolist(), boxes.xyxy.tolist()
        ):
            # El tracker deja huecos en su numeración; se renumera 1, 2, 3...
            track_id = self._ids.setdefault(raw_id, len(self._ids) + 1)
            x1, y1, x2, y2 = (int(round(v)) for v in xyxy)
            box = (max(x1, 0), max(y1, 0), min(x2, w - 1), min(y2, h - 1))
            name = str(self.names[cls])
            det = Detection(track_id, LABELS.get(name.lower(), name), float(conf), box)
            self.trails.setdefault(track_id, deque(maxlen=self._trail)).append(det.center)
            detections.append(det)
        return detections


def draw_detections(frame, detections: list[Detection], trails: dict[int, deque]) -> None:
    """Dibuja sobre ``frame`` las cajas con ID y la estela de cada bache."""
    scale = max(frame.shape[0] / 720, 0.6)
    thick = max(int(round(2 * scale)), 2)
    for det in detections:
        color = PALETTE[det.track_id % len(PALETTE)]
        x1, y1, x2, y2 = det.box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thick)

        points = list(trails.get(det.track_id, ()))
        for a, b in zip(points, points[1:]):
            cv2.line(frame, a, b, color, thick, cv2.LINE_AA)
        cv2.circle(frame, det.center, thick + 2, color, -1, cv2.LINE_AA)

        text = f"{det.label} #{det.track_id}  {det.conf:.2f}"
        font_scale = 0.6 * scale
        (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thick)
        ty = y1 - 6 if y1 - th - 10 > 0 else y1 + th + 10
        cv2.rectangle(frame, (x1, ty - th - 6), (x1 + tw + 8, ty + base), color, -1)
        cv2.putText(frame, text, (x1 + 4, ty - 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                    (255, 255, 255), thick, cv2.LINE_AA)


@dataclass
class _Track:
    track_id: int
    label: str
    first_frame: int
    first_utc: str
    last_frame: int = 0
    last_utc: str = ""
    frames: int = 0
    max_conf: float = 0.0
    best_frame: int = 0
    best_box: tuple[int, int, int, int] = (0, 0, 0, 0)
    best_crop: object = field(default=None, repr=False)


class DetectionLog:
    """Registros de detección de una sesión. Se usa junto a ``SessionRecorder``."""

    def __init__(self, session_dir: Path, width: int, height: int, fps: float, min_frames: int = 3):
        self.dir = Path(session_dir)
        self.min_frames = min_frames
        self.tracks: dict[int, _Track] = {}
        self._writer = AsyncVideoWriter(self.dir / "annotated.mp4", fps, (width, height))
        self._csv_file = open(self.dir / "detections.csv", "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_file)
        self._csv.writerow(["frame", "utc", "track_id", "clase", "confianza", "x1", "y1", "x2", "y2"])

    def unique_count(self) -> int:
        """Baches únicos vistos en al menos ``min_frames`` fotogramas."""
        return sum(1 for t in self.tracks.values() if t.frames >= self.min_frames)

    def add(self, frame_idx: int, utc: str, raw_frame, annotated, detections: list[Detection]) -> None:
        self._writer.write(annotated)
        for det in detections:
            self._csv.writerow([frame_idx, utc, det.track_id, det.label, f"{det.conf:.3f}", *det.box])
            track = self.tracks.get(det.track_id)
            if track is None:
                track = self.tracks[det.track_id] = _Track(det.track_id, det.label, frame_idx, utc)
            track.last_frame, track.last_utc = frame_idx, utc
            track.frames += 1
            if det.conf > track.max_conf:
                track.max_conf, track.best_frame, track.best_box = det.conf, frame_idx, det.box
                track.best_crop = self._crop(raw_frame, det.box)

    @staticmethod
    def _crop(frame, box, margin: float = 0.15):
        x1, y1, x2, y2 = box
        mx, my = int((x2 - x1) * margin), int((y2 - y1) * margin)
        h, w = frame.shape[:2]
        return frame[max(y1 - my, 0):min(y2 + my, h), max(x1 - mx, 0):min(x2 + mx, w)].copy()

    def close(self) -> dict:
        """Cierra los archivos y devuelve el resumen para ``session.json``."""
        self._writer.release()
        self._csv_file.close()

        crops_dir = self.dir / "crops"
        with open(self.dir / "tracks.csv", "w", newline="", encoding="utf-8") as fh:
            out = csv.writer(fh)
            out.writerow(["track_id", "clase", "valido", "frames", "confianza_max", "primer_frame",
                          "ultimo_frame", "primer_utc", "ultimo_utc", "mejor_frame",
                          "x1", "y1", "x2", "y2", "recorte"])
            for t in sorted(self.tracks.values(), key=lambda t: t.track_id):
                crop_name = ""
                if t.best_crop is not None and t.best_crop.size:
                    crops_dir.mkdir(exist_ok=True)
                    crop_name = f"crops/bache_{t.track_id:04d}.jpg"
                    cv2.imwrite(str(self.dir / crop_name), t.best_crop)
                out.writerow([t.track_id, t.label, int(t.frames >= self.min_frames), t.frames,
                              f"{t.max_conf:.3f}", t.first_frame, t.last_frame, t.first_utc,
                              t.last_utc, t.best_frame, *t.best_box, crop_name])
        return {
            "annotated_video": "annotated.mp4",
            "detections_csv": "detections.csv",
            "tracks_csv": "tracks.csv",
            "tracks_total": len(self.tracks),
            "baches_unicos": self.unique_count(),
            "min_frames_valido": self.min_frames,
        }
