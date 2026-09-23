"""Detección y apertura de cámaras locales (webcam integrada, cámaras USB/UVC,
capturadoras HDMI, cámaras de acción en modo webcam, etc.).

Cualquier dispositivo que el sistema operativo exponga como cámara de video
(UVC en Windows/Linux/macOS) es accesible por índice desde OpenCV.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

# Silencia los warnings de OpenCV al sondear índices inexistentes.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("OPENCV_VIDEOIO_PRIORITY_OBSENSOR", "0")

import cv2  # noqa: E402


def default_backend() -> int:
    """Backend de captura recomendado por plataforma.

    En Windows se usa DirectShow: abre los dispositivos más rápido que
    Media Foundation y su orden de índices coincide con el listado de nombres.
    """
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform.startswith("linux"):
        return cv2.CAP_V4L2
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY


@dataclass
class CameraInfo:
    index: int
    name: str
    width: int
    height: int
    fps: float

    def __str__(self) -> str:
        fps = f"{self.fps:.0f} fps" if self.fps > 0 else "fps desconocido"
        return f"[{self.index}] {self.name} — {self.width}x{self.height} @ {fps}"


def _device_names() -> list[str]:
    """Nombres de los dispositivos de video (solo disponible en Windows)."""
    if sys.platform != "win32":
        return []
    try:
        from pygrabber.dshow_graph import FilterGraph

        return list(FilterGraph().get_input_devices())
    except Exception:
        return []


def device_name(index: int) -> str:
    names = _device_names()
    return names[index] if index < len(names) else f"Cámara {index}"


def list_cameras(max_index: int = 10, backend: int | None = None) -> list[CameraInfo]:
    """Sondea los índices 0..max_index-1 y devuelve las cámaras que entregan imagen."""
    backend = default_backend() if backend is None else backend
    names = _device_names()
    found: list[CameraInfo] = []

    # Si conocemos los nombres, sólo sondeamos esa cantidad de índices.
    indices = range(len(names)) if names else range(max_index)
    for index in indices:
        cap = cv2.VideoCapture(index, backend)
        try:
            if not cap.isOpened():
                continue
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            height, width = frame.shape[:2]
            name = names[index] if index < len(names) else f"Cámara {index}"
            found.append(CameraInfo(index, name, width, height, cap.get(cv2.CAP_PROP_FPS)))
        finally:
            cap.release()
    return found


def open_camera(
    index: int,
    width: int | None = None,
    height: int | None = None,
    fps: float | None = None,
    mjpg: bool = True,
    backend: int | None = None,
) -> cv2.VideoCapture:
    """Abre la cámara y solicita resolución/fps. El driver puede ajustar los
    valores pedidos al modo soportado más cercano; consultar el resultado con
    ``cap.get`` o leyendo un fotograma.
    """
    backend = default_backend() if backend is None else backend
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        raise RuntimeError(
            f"No se pudo abrir la cámara {index}. Verificar la conexión o que "
            "no esté en uso por otra aplicación (Zoom, Teams, navegador...)."
        )
    # MJPG permite alta resolución a 30 fps en la mayoría de cámaras USB
    # (en YUY2 sin comprimir el ancho de banda USB lo limita).
    if mjpg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if fps:
        cap.set(cv2.CAP_PROP_FPS, fps)

    ok, _ = cap.read()
    if not ok:
        cap.release()
        raise RuntimeError(f"La cámara {index} se abrió pero no entrega fotogramas.")
    return cap
