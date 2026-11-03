"""SPM — Detección y seguimiento de baches en vivo desde una cámara.

Uso:
    python detect.py --camera 1               # vista previa con detección; R para grabar
    python detect.py --camera 1 --record      # empezar a grabar y registrar de inmediato
    python detect.py --camera 1 --conf 0.4 --imgsz 480

Controles en la vista previa:
    R         iniciar / detener la sesión (video + registros de detección)
    Q / ESC   salir (cierra la sesión en curso)
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

import cv2  # noqa: E402

from spm_capture.cameras import (  # noqa: E402
    LatestFrameGrabber,
    choose_camera,
    device_name,
    list_cameras,
    open_camera,
)
from spm_capture.detection import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    DetectionLog,
    PotholeTracker,
    draw_detections,
    ensure_model,
)
from spm_capture.geometry import CALIBRATION_FILENAME, load_calibration  # noqa: E402
from spm_capture.recorder import AsyncVideoWriter, SessionRecorder  # noqa: E402

WINDOW = "SPM - Deteccion (R: grabar/detener, Q: salir)"
DEFAULT_OUT = Path(__file__).resolve().parent / "recordings"
DEFAULT_CALIBRATION = Path(__file__).resolve().parent / CALIBRATION_FILENAME


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Detección de baches en vivo (SAD Pothole Map).")
    p.add_argument("--camera", type=int, help="Índice de la cámara (ver capture.py --list).")
    p.add_argument("--width", type=int, default=1920, help="Ancho solicitado (default 1920).")
    p.add_argument("--height", type=int, default=1080, help="Alto solicitado (default 1080).")
    p.add_argument("--fps", type=float, default=30, help="FPS solicitados a la cámara.")
    p.add_argument("--no-mjpg", action="store_true", help="No forzar formato MJPG en la cámara.")
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH, help="Pesos YOLO (.pt).")
    p.add_argument("--conf", type=float, default=0.3, help="Confianza mínima (default 0.3).")
    p.add_argument("--imgsz", type=int, default=640, help="Tamaño de entrada del modelo.")
    p.add_argument("--all-classes", action="store_true",
                   help="Detectar todas las clases del modelo, no sólo baches (clase 0).")
    p.add_argument("--tracker", default="bytetrack.yaml", help="bytetrack.yaml o botsort.yaml.")
    p.add_argument("--min-frames", type=int, default=3,
                   help="Fotogramas mínimos para contar un bache como válido (default 3).")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Carpeta de salida.")
    p.add_argument("--record", action="store_true", help="Empezar a grabar inmediatamente.")
    p.add_argument("--no-preview", action="store_true", help="Sin ventana; requiere --record.")
    p.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION,
                   help="Calibración de cámara a copiar en cada sesión "
                        "(default: camera_calibration.json junto a este script, si existe).")
    p.add_argument("--duration", type=float, help="Detener la sesión tras N segundos y salir.")
    return p.parse_args()


def draw_hud(frame, lines: list[str], recording: bool) -> None:
    scale = max(frame.shape[0] / 720, 0.6)
    thick = max(int(round(2 * scale)), 2)
    if recording:
        cv2.circle(frame, (frame.shape[1] - int(30 * scale), int(30 * scale)), int(12 * scale),
                   (0, 0, 255), -1)
    for i, text in enumerate(lines):
        y = int((30 + i * 30) * scale)
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * scale, (0, 0, 0),
                    thick + 2, cv2.LINE_AA)
        cv2.putText(frame, text, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8 * scale, (255, 255, 255),
                    thick, cv2.LINE_AA)


def measure_fps(grabber: LatestFrameGrabber, tracker: PotholeTracker, frames: int = 12) -> float | None:
    """FPS reales de procesamiento, que son los fps a los que se escriben los videos.

    La inferencia es más lenta que la cámara y la codificación de video compite
    por la CPU, así que se mide reproduciendo la carga de una sesión real
    (detección + escritura de los dos videos en archivos temporales).
    """
    seq, start, writers = 0, 0.0, []
    with tempfile.TemporaryDirectory() as tmp:
        try:
            for i in range(frames + 2):
                item = grabber.read(seq)
                if item is None:
                    return None
                frame, _, seq = item
                if not writers:
                    size = (frame.shape[1], frame.shape[0])
                    writers = [AsyncVideoWriter(Path(tmp) / f"{n}.mp4", 10, size) for n in "ab"]
                detections = tracker.update(frame)
                annotated = frame.copy()
                draw_detections(annotated, detections, tracker.trails)
                writers[0].write(frame)
                writers[1].write(annotated)
                if i == 1:  # los primeros fotogramas incluyen la inicialización del modelo
                    start = time.perf_counter()
            return frames / (time.perf_counter() - start)
        finally:
            for writer in writers:
                writer.release()


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

    if args.camera is None:
        print("Buscando cámaras...")
        cameras = list_cameras()
        if not cameras:
            print("No se detectó ninguna cámara.", file=sys.stderr)
            return 1
        selected = choose_camera(cameras)
        index, name = selected.index, selected.name
    else:
        index, name = args.camera, device_name(args.camera)

    try:
        model_path = ensure_model(args.model)
        cap = open_camera(index, args.width, args.height, args.fps, mjpg=not args.no_mjpg)
    except (RuntimeError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Usando {name} (índice {index}). Cargando modelo {model_path.name}...")
    tracker = PotholeTracker(
        model_path,
        conf=args.conf,
        imgsz=args.imgsz,
        classes=None if args.all_classes else [0],
        tracker=args.tracker,
    )
    grabber = LatestFrameGrabber(cap)

    fps = measure_fps(grabber, tracker)
    if fps is None:
        print("La cámara no entrega imagen.", file=sys.stderr)
        grabber.stop()
        cap.release()
        return 1
    frame, _, seq = grabber.read()
    height, width = frame.shape[:2]
    print(f"Resolución {width}x{height}, detección a {fps:.1f} fps.")

    camera_meta = {"index": index, "name": name, "fourcc": "MJPG" if not args.no_mjpg else "default"}
    model_meta = {"model": model_path.name, "conf": args.conf, "imgsz": args.imgsz,
                  "tracker": args.tracker}
    recorder: SessionRecorder | None = None
    log: DetectionLog | None = None

    def start_session() -> tuple[SessionRecorder, DetectionLog]:
        rec = SessionRecorder(args.out, width, height, fps, camera_meta, calibration)
        print(f"● Grabando en {rec.dir}")
        return rec, DetectionLog(rec.dir, width, height, fps, args.min_frames)

    def stop_session(rec: SessionRecorder, dlog: DetectionLog) -> None:
        summary = dlog.close()
        out = rec.close({"detection": {**model_meta, **summary}})
        print(f"■ Sesión guardada: {out} ({rec.frame_count} frames, "
              f"{summary['baches_unicos']} baches únicos)")

    if args.record:
        recorder, log = start_session()

    live_fps, last_t = fps, time.perf_counter()
    try:
        while True:
            item = grabber.read(seq)
            if item is None:
                print("La cámara dejó de entregar imagen (¿se desconectó?).", file=sys.stderr)
                break
            frame, perf, seq = item

            detections = tracker.update(frame)
            annotated = frame.copy()
            draw_detections(annotated, detections, tracker.trails)

            if recorder and log:
                frame_idx, utc = recorder.write(frame, perf)
                log.add(frame_idx, utc, frame, annotated, detections)
                if args.duration and recorder.elapsed() >= args.duration:
                    break

            now = time.perf_counter()
            live_fps = 0.9 * live_fps + 0.1 * (1.0 / max(now - last_t, 1e-6))
            last_t = now

            if args.no_preview:
                continue
            lines = [datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3] + " UTC",
                     f"{width}x{height}  {live_fps:.1f} fps",
                     f"En pantalla: {len(detections)}"]
            if recorder and log:
                el = int(recorder.elapsed())
                lines.insert(0, f"REC {el // 60:02d}:{el % 60:02d}  Baches unicos: {log.unique_count()}")
            draw_hud(annotated, lines, recorder is not None)
            cv2.imshow(WINDOW, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("r"), ord("R")):
                if recorder and log:
                    stop_session(recorder, log)
                    recorder = log = None
                else:
                    recorder, log = start_session()
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if recorder and log:
            stop_session(recorder, log)
        grabber.stop()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
