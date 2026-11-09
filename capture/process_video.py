"""CLI para procesar offline una sesion de captura SPM."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from spm_capture.offline import SeverityConfig, process_session


def process_frame_for_test(
    frame: Any,
    model_path: Path | None = None,
    confidence: float = 0.3,
    image_size: int = 640,
) -> Any:
    """Detecta objetos en un frame y devuelve una copia anotada, sin tracking."""
    if frame is None or not hasattr(frame, "size") or frame.size == 0:
        raise ValueError("El frame debe ser una imagen no vacía de OpenCV.")

    if model_path is None:
        model_path = Path(__file__).resolve().parents[1] / "weights" / "weights_v4_monoclass.pt"
    model_path = Path(model_path)
    if not model_path.is_file():
        raise FileNotFoundError(f"No existe el modelo {model_path}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Falta ultralytics. Instala las dependencias de capture/.") from exc

    model = YOLO(str(model_path))
    result = model.predict(
        source=frame,
        conf=confidence,
        imgsz=image_size,
        verbose=False,
    )[0]
    return result.plot()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detecta, rastrea y georreferencia baches en una sesion de video."
    )
    parser.add_argument("session_dir", type=Path, help="Carpeta con video.mp4 y frames.csv.")
    default_model = Path(__file__).resolve().parents[1] / "weights" / "weights_v4_monoclass.pt"
    parser.add_argument("--model", type=Path, default=default_model,
                        help="Pesos YOLO monoclass pothole (.pt; V4 por defecto).")
    parser.add_argument("--gpx", type=Path, help="Archivo GPX; por defecto, el unico .gpx de la sesion.")
    parser.add_argument("--conf", type=float, default=0.3, help="Confianza minima (default: 0.3).")
    parser.add_argument("--imgsz", type=int, default=640, help="Tamaño de inferencia (default: 640).")
    parser.add_argument("--min-frames", type=int, default=3,
                        help="Observaciones minimas por track (default: 3).")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Tracker de Ultralytics.")
    parser.add_argument("--roi-horizon", type=float, default=0.45,
                        help="Excluir centros por encima de esta fracción de H (provisional: 0.45).")
    parser.add_argument("--area-light", type=float, default=0.001,
                        help="Umbral A_norm leve/moderado (calibración actual: 0.001).")
    parser.add_argument("--area-critical", type=float, default=0.008,
                        help="Umbral A_norm moderado/crítico (calibración actual: 0.008).")
    parser.add_argument("--perspective-reference-y", type=float, default=0.7,
                        help="Fila normalizada de referencia para perspectiva (provisional: 0.7).")
    parser.add_argument("--perspective-exponent", type=float, default=2.0,
                        help="Exponente de corrección de perspectiva (provisional: 2.0).")
    calibration = parser.add_mutually_exclusive_group()
    calibration.add_argument("--calibration", type=Path,
                             help="Calibración de cámara; por defecto, camera_calibration.json "
                                  "de la sesión si existe.")
    calibration.add_argument("--no-calibration", action="store_true",
                             help="Exportar la posición del GPS sin corregir el offset de cámara.")
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
            calibration_path=args.calibration,
            use_calibration=not args.no_calibration,
            severity_config=SeverityConfig(
                roi_horizon_ratio=args.roi_horizon,
                light_area_threshold=args.area_light,
                critical_area_threshold=args.area_critical,
                perspective_reference_ratio=args.perspective_reference_y,
                perspective_exponent=args.perspective_exponent,
            ),
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())