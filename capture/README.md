# SPM — Captura de video (Fase 1)

Herramienta para grabar video desde cualquier cámara conectada al equipo y dejar
los timestamps necesarios para sincronizarlo con el track GPS.

El procesamiento offline de la Fase 5 se ejecuta después sobre una carpeta de
sesión; no modifica ni reemplaza el flujo de captura/detección en vivo.

Acepta cualquier dispositivo que el sistema reconozca como cámara (UVC):
webcam integrada, webcam USB, cámara de acción / dashcam en modo webcam,
capturadora HDMI‑USB para cámaras con salida HDMI, o cámaras virtuales (OBS,
DroidCam para usar un smartphone).

## Instalación

```powershell
cd capture
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```powershell
python capture.py --list                 # ver cámaras detectadas (índice + nombre)
python capture.py                        # elegir cámara y abrir vista previa
python capture.py --camera 1             # usar directamente la cámara 1
python capture.py --camera 1 --width 1280 --height 720 --fps 30
python capture.py --camera 1 --record --no-preview       # grabar sin ventana, Ctrl+C para parar
python capture.py --camera 1 --record --duration 600     # grabar 10 min y salir
```

En la vista previa: **R** inicia/detiene la grabación, **Q** o **ESC** sale.
La superposición (hora UTC, fps, REC) solo se muestra en pantalla, no se graba.

Se piden 1920×1080 @ 30 fps en formato MJPG por defecto; si la cámara no lo
soporta, el driver usa el modo más cercano (se informa al iniciar).
`--no-mjpg` desactiva MJPG si alguna cámara da problemas con ese formato.

## Salida

Cada grabación crea `recordings/sesion_AAAAMMDD_HHMMSS/`:

| Archivo | Contenido |
| --- | --- |
| `video.mp4` | Video grabado. |
| `frames.csv` | `frame, t_rel_s, epoch_s, utc` — hora UTC de cada fotograma. |
| `session.json` | Cámara, resolución, fps nominal y real, duración, inicio/fin UTC. |

`frames.csv` es la referencia para la Fase 5: para ubicar un bache detectado en
el fotograma *N*, se busca su hora UTC y se interpola la posición en el `.gpx`.
Se usa esta tabla (y no `N / fps`) porque las cámaras USB no entregan fps
perfectamente constantes.

## Detección en vivo (`detect.py`)

Corre un modelo YOLO sobre la imagen de la cámara y sigue cada bache con
ByteTrack: en pantalla se ve la caja, un ID (`Bache #3`), la confianza y la
estela del recorrido, como en un tracker.

```powershell
python detect.py --camera 1              # vista previa; R inicia/detiene la sesión
python detect.py --camera 1 --record     # grabar y registrar desde el inicio
python detect.py --camera 1 --conf 0.4   # exigir más confianza (menos falsos positivos)
python detect.py --camera 1 --imgsz 480  # más fps, menos precisión en baches chicos
```

Mientras se graba (tecla **R**), además de `video.mp4`, `frames.csv` y
`session.json`, la carpeta de la sesión incluye:

| Archivo | Contenido |
| --- | --- |
| `annotated.mp4` | Video con cajas, IDs y estelas dibujados. |
| `detections.csv` | Una fila por bache y fotograma: `frame, utc, track_id, clase, confianza, x1, y1, x2, y2`. |
| `tracks.csv` | Una fila por bache único: fotogramas y hora UTC de primera/última vista, confianza máxima, mejor fotograma y recorte. `valido=1` si se vio en al menos `--min-frames` fotogramas (default 3). |
| `crops/bache_NNNN.jpg` | Recorte del fotograma de mayor confianza de cada bache. |

`frame` en `detections.csv` es el mismo índice que en `frames.csv` y `video.mp4`.

**Modelo**: por defecto se descarga en `models/` un YOLO11n público
([tahaUgan/pothole-yolo11n](https://huggingface.co/tahaUgan/pothole-yolo11n),
CC-BY-4.0) como modelo provisional hasta entrenar el propio (Fase 3). Para usar
otro: `--model ruta/al/best.pt`.

**Rendimiento**: en CPU (sin GPU) la detección corre a ~10–13 fps en 1080p;
los videos de la sesión se escriben a esos fps, no a los 30 de la cámara.

## Procesamiento offline (Fase 5)

El modelo multiclase debe incluir exactamente las clases `pothole_light`,
`pothole_moderate` y `pothole_critical`. Instala las dependencias de captura con
`pip install -r requirements.txt` (incluye `gpxpy`) y ejecuta desde `capture/`:

```bash
python process_video.py recordings/sesion_AAAAMMDD_HHMMSS \
   --model ../weights/weights.pt
python process_video.py recordings/sesion_AAAAMMDD_HHMMSS \
   --model ../weights/weights.pt --gpx ruta/al/track.gpx --conf 0.35 --min-frames 3
```

La carpeta debe contener `video.mp4` y `frames.csv`. Si no se indica `--gpx`,
debe existir exactamente un archivo `.gpx` dentro de la sesión. `frames.csv`
asocia cada índice del video con el timestamp UTC capturado; no se calcula el
tiempo GPS como `frame / FPS`, ya que la tasa de reproducción puede diferir del
tiempo real. El FPS del contenedor se valida y se informa como metadato.

Ultralytics ejecuta `model.track` secuencialmente con `persist=True` y
`bytetrack.yaml` por defecto. Por `track_id`, se requiere un mínimo de tres
observaciones (configurable con `--min-frames`), la severidad se decide por
mayoría y los empates por suma de confianza de clase. El timestamp, la posición
y la evidencia corresponden a la observación de mayor confianza. Si ese tiempo
queda fuera de la cobertura GPX, latitud y longitud se exportan como `null`.

La sesión recibe `processed_potholes.json` y `crops/pothole_NNNN.jpg`. Cada
elemento JSON contiene `track_id`, `severity`, `confidence_avg`,
`confidence_max`, `latitude`, `longitude`, `timestamp` UTC, `frame_key`,
`frames_detected` y `evidence_image` (ruta relativa). Este paso solo exporta
datos localmente; no sube imágenes/API ni deduplica detecciones entre sesiones.

## Protocolo de sincronización con el GPS

1. Antes de salir, sincronizar la hora de la laptop (Windows: *Configuración →
   Hora e idioma → Sincronizar ahora*). El GPS toma la hora de los satélites.
2. Iniciar el GPS logger (smartphone o módulo) y esperar fix estable.
3. Iniciar la grabación con `capture.py`.
4. Verificación: filmar unos segundos la pantalla del GPS logger mostrando su
   hora; comparar con la hora en `frames.csv` para medir el desfase residual.
   Si es mayor a ~0,5 s, anotarlo para corregirlo en la georreferenciación.
5. Al terminar, detener la grabación y luego el logger. Guardar el `.gpx` /
   `.csv` del GPS dentro de la carpeta de la sesión.

## Problemas comunes

- **No aparece la cámara**: probar otro puerto/cable USB (algunos cables solo
  cargan, sin datos) y verificar que la cámara esté en modo webcam/UVC.
- **"No se pudo abrir la cámara"**: cerrar otras apps que la estén usando
  (Zoom, Teams, navegador, app Cámara de Windows).
- **fps bajos**: poca luz aumenta la exposición y baja los fps; también el
  puerto USB 2.0 limita la resolución sin MJPG.
