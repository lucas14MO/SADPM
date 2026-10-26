"""CLI para procesar offline una sesion de captura SPM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from spm_capture.offline import process_session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detecta, rastrea y georreferencia baches en una sesion de video."
    )
    parser.add_argument("session_dir", type=Path, help="Carpeta con video.mp4 y frames.csv.")
    parser.add_argument("--model", type=Path, required=True, help="Pesos multiclase YOLO (.pt).")
    parser.add_argument("--gpx", type=Path, help="Archivo GPX; por defecto, el unico .gpx de la sesion.")
    parser.add_argument("--conf", type=float, default=0.3, help="Confianza minima (default: 0.3).")
    parser.add_argument("--imgsz", type=int, default=640, help="Tamaño de inferencia (default: 640).")
    parser.add_argument("--min-frames", type=int, default=3,
                        help="Observaciones minimas por track (default: 3).")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Tracker de Ultralytics.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        process_session(
            args.session_dir,
            args.model,
            gpx_path=args.gpx,
            confidence=args.conf,
            image_size=args.imgsz,
            min_frames=args.min_frames,
            tracker=args.tracker,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())