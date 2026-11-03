"""SPM — Calibración del offset de la cámara respecto de la antena GPS.

Genera ``camera_calibration.json``, que ``capture.py``/``detect.py`` copian en
cada sesión y ``process_video.py`` usa para proyectar cada bache desde la
posición del GPS hasta su ubicación real en la calzada.

Con el vehículo detenido en suelo plano, colocar marcadores (conos, cinta) en
el piso delante de la cámara a distancias medidas, capturar un fotograma y:

    # clic sobre cada marcador en una ventana (orden de --marker)
    python calibrate_camera.py --image frame.jpg --height 1.35 --hfov 78 \\
        --marker 5 --marker 10 --forward-offset 1.2

    # tomar el fotograma 0 del video de una sesión
    python calibrate_camera.py --video recordings/sesion_X/video.mp4 --height 1.35 \\
        --hfov 78 --marker 5 --marker 10

    # sin ventana: distancia_m:fila_px; con 2+ marcadores puede estimar el FOV
    python calibrate_camera.py --image frame.jpg --height 1.35 \\
        --marker 5:812 --marker 10:640 --marker 15:585 --solve-fov

    # inclinación medida con inclinómetro, sin marcadores
    python calibrate_camera.py --height 1.35 --hfov 78 --pitch 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from spm_capture.geometry import (
    CALIBRATION_FILENAME,
    CameraCalibration,
    solve_pitch,
    solve_pitch_and_fov,
)

DEFAULT_OUT = Path(__file__).resolve().parent / CALIBRATION_FILENAME
WINDOW = "SPM - Calibracion (clic en cada marcador, ESC cancela)"
GRID_DISTANCES_M = (3, 5, 10, 15, 20, 30)


def parse_marker(text: str) -> tuple[float, float | None]:
    distance, _, row = text.partition(":")
    try:
        return float(distance), float(row) if row else None
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Marcador inválido '{text}': usar DIST o DIST:FILA") from exc


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Calibra el offset de la cámara (SAD Pothole Map).")
    source = p.add_mutually_exclusive_group()
    source.add_argument("--image", type=Path, help="Fotograma con los marcadores visibles.")
    source.add_argument("--video", type=Path, help="Video del que tomar el fotograma.")
    p.add_argument("--frame", type=int, default=0, help="Índice del fotograma de --video (default 0).")
    p.add_argument("--height", type=float, required=True,
                   help="Altura del lente sobre la calzada, en metros.")
    p.add_argument("--hfov", type=float, help="Campo de visión horizontal de la cámara (grados).")
    p.add_argument("--pitch", type=float,
                   help="Inclinación hacia abajo (grados) medida directamente; omite los marcadores.")
    p.add_argument("--marker", type=parse_marker, action="append", default=[],
                   help="Distancia horizontal (m) desde la vertical del lente a un marcador en el "
                        "piso, opcionalmente con su fila en píxeles: DIST o DIST:FILA. Repetible.")
    p.add_argument("--solve-fov", action="store_true",
                   help="Estimar también el campo de visión (requiere 2+ marcadores).")
    p.add_argument("--forward-offset", type=float, default=0.0,
                   help="Metros que la cámara está DELANTE de la antena GPS (negativo si detrás).")
    p.add_argument("--right-offset", type=float, default=0.0,
                   help="Metros que la cámara está a la DERECHA de la antena GPS (negativo si a la izq.).")
    p.add_argument("--yaw", type=float, default=0.0,
                   help="Giro de la cámara hacia la derecha respecto del eje del vehículo (grados).")
    p.add_argument("--time-offset", type=float, default=0.0,
                   help="Segundos a sumar a la hora de cada fotograma para alinearla con el GPS "
                        "(hora_GPS - hora_equipo, ver protocolo de sincronización).")
    p.add_argument("--max-distance", type=float, default=30.0,
                   help="Distancia máxima de proyección confiable en metros (default 30).")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Archivo de salida.")
    p.add_argument("--check", type=Path,
                   help="Guardar el fotograma con la grilla de distancias proyectada.")
    p.add_argument("--no-gui", action="store_true", help="No abrir ventanas.")
    return p.parse_args()


def load_frame(args: argparse.Namespace) -> Any | None:
    if args.image is None and args.video is None:
        return None
    import cv2

    if args.image is not None:
        frame = cv2.imread(str(args.image))
        if frame is None:
            raise OSError(f"No se pudo leer la imagen: {args.image}")
        return frame
    capture = cv2.VideoCapture(str(args.video))
    try:
        if not capture.isOpened():
            raise OSError(f"No se pudo abrir el video: {args.video}")
        capture.set(cv2.CAP_PROP_POS_FRAMES, args.frame)
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok:
        raise OSError(f"No se pudo leer el fotograma {args.frame} de {args.video}")
    return frame


def click_markers(frame: Any, distances: list[float]) -> list[float]:
    """Pide un clic por marcador y devuelve la fila (v) de cada uno."""
    import cv2

    rows: list[float] = []
    clicked: list[tuple[int, int]] = []

    def on_mouse(event: int, x: int, y: int, *_: Any) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(clicked) < len(distances):
            clicked.append((x, y))

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, on_mouse)
    try:
        while len(clicked) < len(distances):
            view = frame.copy()
            for (x, y), distance in zip(clicked, distances):
                cv2.drawMarker(view, (x, y), (0, 255, 0), cv2.MARKER_CROSS, 30, 2)
                cv2.putText(view, f"{distance:g} m", (x + 12, y - 12), cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, (0, 255, 0), 2, cv2.LINE_AA)
            prompt = f"Clic en el marcador a {distances[len(clicked)]:g} m"
            cv2.putText(view, prompt, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5, cv2.LINE_AA)
            cv2.putText(view, prompt, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2,
                        cv2.LINE_AA)
            cv2.imshow(WINDOW, view)
            if cv2.waitKey(20) & 0xFF == 27:
                raise KeyboardInterrupt
        rows = [float(y) for _, y in clicked]
    finally:
        cv2.destroyWindow(WINDOW)
    return rows


def draw_grid(frame: Any, calibration: CameraCalibration) -> Any:
    """Dibuja las líneas de distancia (desde la cámara) que predice la calibración."""
    import math

    import cv2

    view = frame.copy()
    height, width = view.shape[:2]
    focal = calibration.focal_px(width)
    pitch = math.radians(calibration.pitch_deg)
    for distance in GRID_DISTANCES_M:
        angle = math.atan2(calibration.camera_height_m, distance) - pitch
        row = int(round(height / 2 + focal * math.tan(angle)))
        if 0 <= row < height:
            cv2.line(view, (0, row), (width, row), (0, 200, 255), 2, cv2.LINE_AA)
            cv2.putText(view, f"{distance} m", (12, row - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 200, 255), 2, cv2.LINE_AA)
    return view


def main() -> int:
    args = parse_args()
    try:
        frame = load_frame(args)
        if args.pitch is not None:
            if args.hfov is None:
                raise ValueError("--pitch requiere --hfov.")
            pitch, hfov, residuals = args.pitch, args.hfov, []
        else:
            if not args.marker:
                raise ValueError("Indicar --pitch o al menos un --marker.")
            if frame is None:
                raise ValueError("Los marcadores requieren --image o --video (para conocer la resolución).")
            image_height, image_width = frame.shape[:2]
            distances = [distance for distance, _ in args.marker]
            rows = [row for _, row in args.marker]
            if any(row is None for row in rows):
                if args.no_gui:
                    raise ValueError("Con --no-gui los marcadores deben indicarse como DIST:FILA.")
                rows = click_markers(frame, distances)
            markers = list(zip(distances, rows))
            if args.solve_fov:
                pitch, hfov, residuals = solve_pitch_and_fov(markers, args.height, image_width, image_height)
            else:
                if args.hfov is None:
                    raise ValueError("Indicar --hfov o usar --solve-fov con 2+ marcadores.")
                hfov = args.hfov
                pitch, residuals = solve_pitch(markers, args.height, image_width, image_height, hfov)
            for (distance, row), residual in zip(markers, residuals):
                print(f"  marcador {distance:6.2f} m  fila {row:7.1f} px  error {residual:+.2f} m")

        calibration = CameraCalibration(
            camera_height_m=args.height,
            pitch_deg=round(pitch, 3),
            hfov_deg=hfov,
            forward_offset_m=args.forward_offset,
            right_offset_m=args.right_offset,
            yaw_deg=args.yaw,
            time_offset_s=args.time_offset,
            max_distance_m=args.max_distance,
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        calibration.save(args.out)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Calibración cancelada.", file=sys.stderr)
        return 1

    print(f"Inclinación {calibration.pitch_deg:.2f}°, FOV horizontal {calibration.hfov_deg:.2f}°")
    if residuals and max(abs(value) for value in residuals) > 0.5:
        print("Aviso: algún marcador tiene error > 0,5 m; revisar altura, FOV o las mediciones.")
    print(f"Calibración guardada en {args.out}")

    if frame is not None:
        check = draw_grid(frame, calibration)
        if args.check:
            import cv2

            cv2.imwrite(str(args.check), check)
            print(f"Grilla de verificación: {args.check}")
        if not args.no_gui:
            import cv2

            cv2.imshow("SPM - Verificacion (cualquier tecla cierra)", check)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
