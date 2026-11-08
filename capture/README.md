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
| `session.json` | Cámara, resolución, fps nominal y real, duración, inicio/fin UTC y calibración usada. |
| `camera_calibration.json` | Copia de la calibración de cámara vigente (si existe, ver más abajo). |

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

El modelo offline predeterminado es `../weights/weights_v4_monoclass.pt` (YOLO26
Small, clase única `pothole`). Instala las dependencias de captura con
`pip install -r requirements.txt` (incluye `gpxpy`) y ejecuta desde `capture/`:

```bash
python process_video.py recordings/sesion_AAAAMMDD_HHMMSS
python process_video.py recordings/sesion_AAAAMMDD_HHMMSS \
   --model ../weights/weights_v4_monoclass.pt --gpx ruta/al/track.gpx --conf 0.35 --min-frames 3
```

La carpeta debe contener `video.mp4` y `frames.csv`. Si no se indica `--gpx`,
debe existir exactamente un archivo `.gpx` dentro de la sesión. `frames.csv`
asocia cada índice del video con el timestamp UTC capturado; no se calcula el
tiempo GPS como `frame / FPS`, ya que la tasa de reproducción puede diferir del
tiempo real. El FPS del contenedor se valida y se informa como metadato.

Ultralytics ejecuta `model.track` secuencialmente con `persist=True`,
`bytetrack.yaml` y la clase `pothole`. Se descartan observaciones cuyo centro
vertical esté por encima de `--roi-horizon × H` (default provisional `0.45`).
Por `track_id`, se requiere un mínimo de tres observaciones dentro de la ROI
(configurable con `--min-frames`). El keyframe es la observación de mayor área
de caja; los empates se resuelven por confianza. Severidad, caja/evidencia,
timestamp y posición corresponden a ese mismo keyframe.

Para el keyframe se calcula `A = (x2-x1) × (y2-y1)` y
`A_norm = A / (W × H) × f(Y_center)`. La función aplicada inicialmente es
`f(y) = ((y_ref-y_roi)/(y-y_roi))^p`, limitada cerca del horizonte para evitar
singularidades. La ROI (`--roi-horizon`), los umbrales `--area-light`/
`--area-critical`, la fila `--perspective-reference-y` y el exponente
`--perspective-exponent` son configurables y tienen valores **provisionales**;
no se han calibrado con recorridos etiquetados. `A_norm` menor al primer umbral
produce `leve`; entre umbrales, `moderado`; desde el segundo, `critico`.
La confianza YOLO se conserva separada de la severidad (`confidence_avg`,
`confidence_max` y `confidence_keyframe`).

Si el timestamp del keyframe queda fuera de la cobertura GPX, latitud y longitud
se exportan como `null`.

La sesión recibe `processed_potholes.json` y `crops/bache_NNNN.jpg`, con la caja
dibujada sobre la evidencia. Cada
elemento JSON contiene `track_id`, `severity`, `confidence_avg`,
`confidence_max`, `confidence_keyframe`, `area_norm`, `latitude`, `longitude`,
`timestamp` UTC, `frame_key`, `frames_detected` y `evidence_image` (ruta
relativa). La exportación es local; la importación backend copia la imagen a
MEDIA y deduplica detecciones entre sesiones.

Si la sesión tiene `camera_calibration.json` (o se indica `--calibration`),
`latitude`/`longitude` son la posición **corregida del bache** y no la de la
antena GPS (ver *Calibración del offset de cámara*). Cada elemento agrega:

| Campo | Contenido |
| --- | --- |
| `location_method` | `camera_projection` (posición corregida) o `gps_vehicle` (posición del GPS sin corregir). |
| `vehicle_latitude`, `vehicle_longitude` | Posición de la antena GPS en el mejor fotograma. |
| `projected_samples` | Proyecciones usadas para la posición calibrada; actualmente una, la del keyframe. |

`--no-calibration` exporta la posición del GPS aunque exista calibración.

## Calibración del offset de cámara

La coordenada del GPX es la de la antena (teléfono/módulo), pero el bache está
varios metros adelante en la imagen: sin corrección, cada bache queda
desplazado hacia atrás en el mapa (típicamente 5–15 m). La calibración describe
cómo está montada la cámara para proyectar cada detección sobre la calzada.

**Una vez por montaje** (si se mueve la cámara, recalibrar):

1. Vehículo detenido en suelo plano. Medir:
   - altura del lente sobre el piso (`--height`, m);
   - posición de la cámara respecto de la antena GPS: metros hacia adelante
     (`--forward-offset`, negativo si la cámara está detrás) y a la derecha
     (`--right-offset`).
2. Colocar 2–3 marcadores (conos, cinta) en el piso, delante de la cámara, a
   distancias medidas **desde la vertical del lente** (ej. 4, 8 y 15 m).
3. Grabar unos segundos con la misma resolución que se usará en campo y calibrar
   haciendo clic sobre cada marcador:

```powershell
python calibrate_camera.py --video recordings/sesion_X/video.mp4 --height 1.35 `
    --hfov 78 --marker 4 --marker 8 --marker 15 --forward-offset 1.2
# Si no se conoce el FOV de la cámara, estimarlo con 2+ marcadores:
python calibrate_camera.py --image frame.jpg --height 1.35 `
    --marker 4 --marker 8 --marker 15 --solve-fov
# Sin ventana: DIST:FILA (fila en píxeles del marcador)
python calibrate_camera.py --image frame.jpg --height 1.35 --hfov 78 --no-gui `
    --marker 4:944 --marker 8:733
```

Se informa el error de cada marcador (debe ser < 0,5 m) y se muestra la grilla
de distancias proyectada (`--check grilla.jpg` la guarda). El resultado,
`camera_calibration.json` junto a los scripts, tiene esta forma:

```jsonc
{
  "camera_height_m": 1.35,     // altura del lente
  "pitch_deg": 12.4,           // inclinación hacia abajo (calculada)
  "hfov_deg": 78.0,            // campo de visión horizontal
  "forward_offset_m": 1.2,     // cámara delante (+) de la antena GPS
  "right_offset_m": 0.0,       // cámara a la derecha (+) de la antena
  "yaw_deg": 0.0,              // giro de la cámara a la derecha (+)
  "time_offset_s": 0.0,        // hora GPS − hora del equipo
  "max_distance_m": 30.0       // proyecciones más lejanas se descartan
}
```

`time_offset_s` corrige el desfase de reloj medido en el paso 4 del protocolo
de sincronización: a 40 km/h, 0,5 s de desfase son ~5,5 m de error.

`capture.py` y `detect.py` copian automáticamente `camera_calibration.json` a
cada sesión (u otro archivo con `--calibration`), de modo que cada grabación
conserva el montaje con que se hizo. `process_video.py` lo usa así:

1. Proyecta el centro de la caja de cada observación sobre el piso (modelo
   pinhole sobre suelo plano) y suma el offset de montaje.
2. Calcula el rumbo del vehículo con el GPX (posiciones a ±1 s).
3. Desplaza la posición de la antena según ese rumbo.
4. Promedia las observaciones ponderando por `1 / (h² + d²)`: las cercanas son
   mucho más precisas (1° de error de inclinación son ~0,4 m a 5 m, pero ~5 m a
   20 m). Se prefieren las cajas que no tocan el borde de la imagen.

Si el vehículo está detenido (sin rumbo fiable) o no hay proyecciones válidas,
se usa la posición del GPS (`location_method: "gps_vehicle"`).

Limitaciones: supone calzada plana, punto principal en el centro de la imagen y
lente sin distorsión fuerte (cámaras gran angular/ojo de pez requieren
corrección previa). El GPS de un teléfono tiene por sí mismo 3–5 m de error.

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
