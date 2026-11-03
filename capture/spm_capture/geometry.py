"""Calibración de la cámara y compensación de posición (offset) de las detecciones.

La coordenada del GPX corresponde a la antena del GPS, pero el bache detectado
está varios metros delante, en el campo de visión de la cámara. Este módulo
proyecta el píxel de la detección sobre la calzada (modelo pinhole sobre suelo
plano) y lo convierte en un desplazamiento respecto de la antena:

    adelante_m, derecha_m = calibracion.project_pixel(u, v, ancho, alto)

Con el rumbo (*heading*) del vehículo, ese desplazamiento se traslada a
latitud/longitud con :func:`offset_position`.

Convenciones:

- Ejes del vehículo: adelante (+), derecha (+), abajo (+).
- ``pitch_deg``: inclinación del eje óptico por debajo del horizonte.
- ``yaw_deg``: giro del eje óptico hacia la derecha del eje del vehículo.
- ``heading``: grados desde el norte en sentido horario (0 = N, 90 = E).
- Se asumen píxeles cuadrados, punto principal en el centro de la imagen y
  lente sin distorsión significativa.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Sequence

EARTH_RADIUS_M = 6_371_008.8
CALIBRATION_FILENAME = "camera_calibration.json"


@dataclass(frozen=True)
class CameraCalibration:
    camera_height_m: float
    pitch_deg: float
    hfov_deg: float
    forward_offset_m: float = 0.0
    right_offset_m: float = 0.0
    yaw_deg: float = 0.0
    time_offset_s: float = 0.0
    max_distance_m: float = 30.0

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Calibración: '{item.name}' debe ser un número finito.")
        if self.camera_height_m <= 0:
            raise ValueError("Calibración: camera_height_m debe ser mayor que cero.")
        if not 0 < self.hfov_deg < 180:
            raise ValueError("Calibración: hfov_deg debe estar entre 0 y 180.")
        if not -90 < self.pitch_deg < 90:
            raise ValueError("Calibración: pitch_deg debe estar entre -90 y 90.")
        if not -90 < self.yaw_deg < 90:
            raise ValueError("Calibración: yaw_deg debe estar entre -90 y 90.")
        if self.max_distance_m <= 0:
            raise ValueError("Calibración: max_distance_m debe ser mayor que cero.")

    @classmethod
    def from_dict(cls, data: Any) -> CameraCalibration:
        if not isinstance(data, dict):
            raise ValueError("La calibración debe ser un objeto JSON.")
        known = {item.name for item in fields(cls)}
        try:
            return cls(**{key: value for key, value in data.items() if key in known})
        except TypeError as exc:
            raise ValueError(f"Calibración incompleta: {exc}") from exc

    @classmethod
    def load(cls, path: Path) -> CameraCalibration:
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} no es JSON válido: {exc}") from exc
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    def focal_px(self, image_width: int) -> float:
        return focal_from_hfov(self.hfov_deg, image_width)

    def project_pixel(
        self, u: float, v: float, image_width: int, image_height: int
    ) -> tuple[float, float, float] | None:
        """Proyecta el píxel ``(u, v)`` sobre la calzada.

        Devuelve ``(adelante_m, derecha_m, distancia_m)``: los dos primeros son
        relativos a la antena GPS (incluyen el offset de montaje) y la distancia
        es la horizontal entre la cámara y el punto. Devuelve ``None`` si el
        píxel está sobre el horizonte o más lejos que ``max_distance_m``.
        """
        focal = self.focal_px(image_width)
        x_n = (u - image_width / 2) / focal
        y_n = (v - image_height / 2) / focal
        pitch = math.radians(self.pitch_deg)
        down = math.sin(pitch) + y_n * math.cos(pitch)
        if down <= 1e-9:
            return None
        scale = self.camera_height_m / down
        forward = scale * (math.cos(pitch) - y_n * math.sin(pitch))
        right = scale * x_n
        distance = math.hypot(forward, right)
        if forward <= 0 or distance > self.max_distance_m:
            return None
        yaw = math.radians(self.yaw_deg)
        forward, right = (
            forward * math.cos(yaw) - right * math.sin(yaw),
            forward * math.sin(yaw) + right * math.cos(yaw),
        )
        return forward + self.forward_offset_m, right + self.right_offset_m, distance


def load_calibration(path: Path | None, required: bool = True) -> CameraCalibration | None:
    """Carga la calibración; si no es ``required`` y el archivo no existe, devuelve ``None``."""
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"No existe el archivo de calibración: {path}")
        return None
    return CameraCalibration.load(path)


def focal_from_hfov(hfov_deg: float, image_width: int) -> float:
    return (image_width / 2) / math.tan(math.radians(hfov_deg) / 2)


def local_offset_m(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Desplazamiento ``(norte_m, este_m)`` del punto 2 respecto del 1 (aprox. plana)."""
    mean_lat = math.radians((lat1 + lat2) / 2)
    north = math.radians(lat2 - lat1) * EARTH_RADIUS_M
    east = math.radians(lon2 - lon1) * EARTH_RADIUS_M * math.cos(mean_lat)
    return north, east


def offset_position(
    latitude: float, longitude: float, heading_deg: float, forward_m: float, right_m: float
) -> tuple[float, float]:
    """Traslada una posición ``forward_m`` adelante y ``right_m`` a la derecha del rumbo."""
    heading = math.radians(heading_deg)
    north = forward_m * math.cos(heading) - right_m * math.sin(heading)
    east = forward_m * math.sin(heading) + right_m * math.cos(heading)
    new_latitude = latitude + math.degrees(north / EARTH_RADIUS_M)
    new_longitude = longitude + math.degrees(
        east / (EARTH_RADIUS_M * math.cos(math.radians(latitude)))
    )
    return new_latitude, new_longitude


def solve_pitch(
    markers: Sequence[tuple[float, float]],
    camera_height_m: float,
    image_width: int,
    image_height: int,
    hfov_deg: float,
) -> tuple[float, list[float]]:
    """Calcula la inclinación a partir de marcadores en el piso.

    ``markers`` son pares ``(distancia_m, fila_px)``: distancia horizontal desde
    la vertical de la cámara hasta el marcador y fila ``v`` donde aparece en la
    imagen. La distancia sobre el suelo depende solo de la fila, por lo que la
    columna no influye. Devuelve ``(pitch_deg, residuos_m)`` donde cada residuo
    es la distancia proyectada menos la medida.
    """
    if not markers:
        raise ValueError("Se necesita al menos un marcador.")
    if any(distance <= 0 for distance, _ in markers):
        raise ValueError("Las distancias de los marcadores deben ser positivas.")
    focal = focal_from_hfov(hfov_deg, image_width)
    center = image_height / 2
    angles = [
        math.atan2(camera_height_m, distance) - math.atan((row - center) / focal)
        for distance, row in markers
    ]
    pitch = sum(angles) / len(angles)
    residuals = []
    for distance, row in markers:
        total = pitch + math.atan((row - center) / focal)
        projected = camera_height_m / math.tan(total) if total > 0 else math.inf
        residuals.append(projected - distance)
    return math.degrees(pitch), residuals


def solve_pitch_and_fov(
    markers: Sequence[tuple[float, float]],
    camera_height_m: float,
    image_width: int,
    image_height: int,
    hfov_range: tuple[float, float] = (30.0, 150.0),
    step_deg: float = 0.05,
) -> tuple[float, float, list[float]]:
    """Ajusta inclinación y campo de visión con dos o más marcadores.

    Busca el ``hfov`` que minimiza el error cuadrático de distancia. Devuelve
    ``(pitch_deg, hfov_deg, residuos_m)``.
    """
    if len({row for _, row in markers}) < 2:
        raise ValueError("Para estimar el campo de visión se necesitan 2 marcadores en filas distintas.")
    best: tuple[float, float, float, list[float]] | None = None
    hfov = hfov_range[0]
    while hfov <= hfov_range[1]:
        pitch, residuals = solve_pitch(markers, camera_height_m, image_width, image_height, hfov)
        error = sum(value * value for value in residuals)
        if math.isfinite(error) and (best is None or error < best[0]):
            best = (error, pitch, hfov, residuals)
        hfov += step_deg
    if best is None:
        raise ValueError("No se encontró una calibración consistente con los marcadores.")
    return best[1], round(best[2], 2), best[3]
