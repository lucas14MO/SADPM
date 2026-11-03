"""SPM — Fase 1: captura de video desde una cámara conectada al equipo.

Uso:
    python capture.py --list                  # listar cámaras detectadas
    python capture.py                         # elegir cámara y abrir vista previa
    python capture.py --camera 1 --width 1920 --height 1080 --fps 30
    python capture.py --camera 1 --record --no-preview   # grabar sin ventana (Ctrl+C para parar)
    python capture.py --camera 1 --record --duration 600 # grabar 10 minutos y salir

Controles en la vista previa:
    R         iniciar / detener grabación
    Q / ESC   salir (cierra la grabación en curso)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2  # noqa: E402

from spm_capture.cameras import choose_camera, device_name, list_cameras, open_camera
from spm_capture.geometry import CALIBRATION_FILENAME, load_calibration
from spm_capture.recorder import SessionRecorder

WINDOW = "SPM - Captura (R: grabar/detener, Q: salir)"
DEFAULT_OUT = Path(__file__).resolve().parent / "recordings"
DEFAULT_CALIBRATION = Path(__file__).resolve().parent / CALIBRATION_FILENAME


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Captura de video para SAD Pothole Map (Fase 1).")
    p.add_argument("--list", action="store_true", help="Listar cámaras disponibles y salir.")
    p.add_argument("--camera", type=int, help="Índice de la cámara a usar (ver --list).")
    p.add_argument("--width", type=int, default=1920, help="Ancho solicitado (default 1920).")
    p.add_argument("--height", type=int, default=1080, help="Alto solicitado (default 1080).")
    p.add_argument("--fps", type=float, default=30, help="FPS solicitados (default 30).")
    p.add_argument("--no-mjpg", action="store_true", help="No forzar formato MJPG en la cámara.")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Carpeta de salida.")
    p.add_argument("--record", action="store_true", help="Empezar a grabar inmediatamente.")
    p.add_argument("--no-preview", action="store_true", help="Sin ventana; requiere --record.")
    p.add_argument("--duration", type=float, help="Detener la grabación tras N segundos y salir.")
    p.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION,
                   help="Calibración de cámara a copiar en cada sesión "
                        "(default: camera_calibration.json junto a este script, si existe).")
    p.add_argument("--max-index", type=int, default=10, help="Índices a sondear si no hay nombres.")
    return p.parse_args()


def measure_fps(cap: cv2.VideoCapture, seconds: float = 1.5) -> float:
    """FPS reales que entrega la cámara (pueden diferir de los reportados por el driver)."""
    for _ in range(5):  # descartar fotogramas iniciales (autoexposición)
        cap.read()
    frames, start = 0, time.perf_counter()
    while time.perf_counter() - start < seconds:
        ok, _ = cap.read()
        if ok:
            frames += 1
    elapsed = time.perf_counter() - start
    return frames / elapsed if elapsed > 0 else 0.0


def draw_overlay(frame, recorder: SessionRecorder | None, live_fps: float):
    """Superpone información en la vista previa (no se graba en el video)."""
    view = frame.copy()
    utc = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3] + " UTC"
    h, w = view.shape[:2]
    lines = [utc, f"{w}x{h}  {live_fps:.1f} fps"]
    if recorder:
        el = int(recorder.elapsed())
        lines.insert(0, f"REC {el // 60:02d}:{el % 60:02d}  ({recorder.frame_count} frames)")
        cv2.circle(view, (w - 30, 30), 12, (0, 0, 255), -1)
    for i, text in enumerate(lines):
        y = 30 + i * 30
        cv2.putText(view, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(view, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    return view


def main() -> int:
    args = parse_args()
    if args.no_preview and not args.record:
        print("--no-preview requiere --record.", file=sys.stderr)
        return 2

    try:
        calibration = load_calibration(args.calibration,
                                       required=args.calibration != DEFAULT_CALIBRATION)
    except (OSError, ValueError) as exc:
        print(f"Calibración inválida: {exc}", file=sys.stderr)
        return 1
    if calibration is None:
        print("Sin calibración de cámara (ver calibrate_camera.py); se grabará igual.")
    else:
        print(f"Calibración de cámara: {args.calibration}")

    if args.camera is None or args.list:
        print("Buscando cámaras...")
        cameras = list_cameras(args.max_index)
        if not cameras:
            print("No se detectó ninguna cámara. Verificar el cable/driver y que la cámara "
                  "esté en modo webcam (UVC).", file=sys.stderr)
            return 1
        if args.list:
            for cam in cameras:
                print(f"  {cam}")
            return 0
        selected = choose_camera(cameras)
        index, name = selected.index, selected.name
    else:
        index, name = args.camera, device_name(args.camera)

    try:
        cap = open_camera(index, args.width, args.height, args.fps, mjpg=not args.no_mjpg)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    ok, frame = cap.read()
    height, width = frame.shape[:2]
    print(f"Usando {name} (índice {index}). Midiendo fps...")
    fps = measure_fps(cap) or args.fps
    print(f"Resolución {width}x{height}, {fps:.1f} fps reales.")

    camera_meta = {"index": index, "name": name, "fourcc": "MJPG" if not args.no_mjpg else "default"}
    recorder: SessionRecorder | None = None

    def start_recording() -> SessionRecorder:
        rec = SessionRecorder(args.out, width, height, fps, camera_meta, calibration)
        print(f"● Grabando en {rec.dir}")
        return rec

    def stop_recording(rec: SessionRecorder) -> None:
        out = rec.close()
        print(f"■ Grabación guardada: {out} ({rec.frame_count} frames)")

    if args.record:
        recorder = start_recording()

    live_fps, last_t, failures = fps, time.perf_counter(), 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                failures += 1
                if failures > 30:
                    print("La cámara dejó de entregar imagen (¿se desconectó?).", file=sys.stderr)
                    break
                continue
            failures = 0

            now = time.perf_counter()
            live_fps = 0.9 * live_fps + 0.1 * (1.0 / max(now - last_t, 1e-6))
            last_t = now

            if recorder:
                recorder.write(frame)
                if args.duration and recorder.elapsed() >= args.duration:
                    break

            if args.no_preview:
                continue
            cv2.imshow(WINDOW, draw_overlay(frame, recorder, live_fps))
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("r"), ord("R")):
                if recorder:
                    stop_recording(recorder)
                    recorder = None
                else:
                    recorder = start_recording()
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if recorder:
            stop_recording(recorder)
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
