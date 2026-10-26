"""Grabación de sesiones de captura en campo.

Cada sesión genera una carpeta con:

- ``video.mp4``   — el video grabado.
- ``frames.csv``  — timestamp UTC de cada fotograma (``frame -> hora``), usado en
  la Fase 5 para interpolar la posición GPS de cada detección.
- ``session.json`` — metadatos: cámara, resolución, fps medidos, inicio/fin UTC.

Los timestamps se calculan con un reloj monotónico anclado a la hora del sistema
al inicio de la sesión, por lo que no saltan si el reloj del sistema se ajusta
durante la grabación. Para que coincidan con el GPX, la hora del equipo debe
estar sincronizada (ver README, protocolo de sincronización).
"""

from __future__ import annotations

import csv
import json
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="milliseconds")


class AsyncVideoWriter:
    """``cv2.VideoWriter`` que codifica en un hilo aparte para no frenar la captura.

    La cola es acotada: si el disco/codificador no da abasto, ``write`` espera
    en lugar de acumular fotogramas en memoria.
    """

    def __init__(self, path: Path, fps: float, size: tuple[int, int], max_queue: int = 30) -> None:
        self._writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
        if not self._writer.isOpened():
            raise RuntimeError(f"No se pudo crear el archivo de video {path}")
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while (frame := self._queue.get()) is not None:
            self._writer.write(frame)

    def write(self, frame) -> None:
        self._queue.put(frame)

    def release(self) -> None:
        self._queue.put(None)
        self._thread.join()
        self._writer.release()


class SessionRecorder:
    def __init__(
        self,
        output_dir: Path,
        width: int,
        height: int,
        fps: float,
        camera: dict,
    ) -> None:
        self.start_epoch = time.time()
        self._start_perf = time.perf_counter()
        stamp = datetime.fromtimestamp(self.start_epoch).strftime("%Y%m%d_%H%M%S")
        self.dir = Path(output_dir) / f"sesion_{stamp}"
        self.dir.mkdir(parents=True, exist_ok=True)

        self.width, self.height, self.fps = width, height, fps
        self.camera = camera
        self.frame_count = 0

        self.video_path = self.dir / "video.mp4"
        self._writer = AsyncVideoWriter(self.video_path, fps, (width, height))

        self._csv_file = open(self.dir / "frames.csv", "w", newline="", encoding="utf-8")
        self._csv = csv.writer(self._csv_file)
        self._csv.writerow(["frame", "t_rel_s", "epoch_s", "utc"])

    def elapsed(self) -> float:
        return time.perf_counter() - self._start_perf

    def write(self, frame, perf: float | None = None) -> tuple[int, str]:
        """Agrega un fotograma. ``perf`` es el ``time.perf_counter()`` del momento
        de captura; si se omite se usa el instante actual.

        Devuelve el índice del fotograma y su hora UTC.
        """
        t_rel = self.elapsed() if perf is None else max(perf - self._start_perf, 0.0)
        epoch = self.start_epoch + t_rel
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        self._writer.write(frame)
        index, utc = self.frame_count, _iso(epoch)
        self._csv.writerow([index, f"{t_rel:.4f}", f"{epoch:.4f}", utc])
        self.frame_count += 1
        return index, utc

    def close(self, extra: dict | None = None) -> Path:
        duration = self.elapsed()
        self._writer.release()
        self._csv_file.close()
        metadata = {
            "camera": self.camera,
            "video": self.video_path.name,
            "frames_csv": "frames.csv",
            "resolution": [self.width, self.height],
            "fps_nominal": round(self.fps, 3),
            "fps_real": round(self.frame_count / duration, 3) if duration > 0 else None,
            "frames": self.frame_count,
            "duration_s": round(duration, 3),
            "start_utc": _iso(self.start_epoch),
            "end_utc": _iso(self.start_epoch + duration),
            "clock_source": "system",
            **(extra or {}),
        }
        with open(self.dir / "session.json", "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2, ensure_ascii=False)
        return self.dir
