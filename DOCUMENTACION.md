# SAD Pothole Map (SPM) — Documentación técnica del estado actual

Este documento describe lo que **ya está implementado** y cómo se relacionan los
tiempos (timestamps) del video con el GPS. Para el plan completo ver [fases.md](fases.md).

## 1. Estado por fase

| Fase | Qué es | Estado |
| --- | --- | --- |
| 1 | Captura de video + timestamps por fotograma | ✅ Hecho (`capture/capture.py`) |
| 1 | Captura del GPS (`.gpx`) | ⚠️ Externo: se hace con una app/módulo GPS logger; **no hay código** |
| 2 | Dataset y etiquetado | ⏳ Pendiente |
| 3 | Entrenamiento propio | ⏳ Pendiente (hoy se usa un modelo público provisional) |
| 4 | Clasificación de gravedad | ⏳ Pendiente |
| 5 | Detección + tracking | ✅ En vivo (`capture/detect.py`) |
| 5 | **Georreferenciación (unir detecciones con GPS)** | ❌ **No implementada todavía** |
| 6 | Deduplicación espacial (DBSCAN) | ⏳ Pendiente |
| 7 | Backend Django REST | ✅ Hecho (`backend/`, ver [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)) |
| 8 | Frontend mapa (React + Leaflet) | ✅ Base hecha con datos mock (`frontend/`) |
| 9 | Integración end-to-end | ⏳ Pendiente |

> **Importante:** hoy el sistema **no guarda coordenadas GPS** en ningún archivo.
> Lo que sí guarda es la hora UTC exacta de cada fotograma, que es lo necesario
> para asignar el GPS después (sección 4).

## 2. Cómo se usa

Instalación (una vez):

```powershell
cd capture
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Solo grabar video + tiempos:

```powershell
python capture.py --list                              # ver cámaras (índice + nombre)
python capture.py --camera 1                          # vista previa; R graba / detiene; Q sale
python capture.py --camera 1 --record --duration 600  # grabar 10 min y salir
python capture.py --camera 1 --record --no-preview    # sin ventana; Ctrl+C para parar
```

Grabar + detectar baches con seguimiento:

```powershell
python detect.py --camera 1                # vista previa; R inicia/detiene la sesión
python detect.py --camera 1 --record       # empieza a grabar de inmediato
python detect.py --camera 1 --conf 0.4     # más confianza mínima = menos falsos positivos
python detect.py --camera 1 --imgsz 480    # más fps, menos precisión en baches chicos
```

Opciones comunes: `--width/--height/--fps` (default 1920×1080 @ 30, MJPG),
`--out` (carpeta de salida, default `capture/recordings`), `--no-mjpg`.
Opciones de `detect.py`: `--model` (pesos `.pt`), `--conf` (default 0.3),
`--imgsz` (default 640), `--min-frames` (default 3, fotogramas mínimos para
considerar válido un bache), `--tracker` (`bytetrack.yaml` o `botsort.yaml`),
`--all-classes` (no filtrar sólo baches).

## 3. Qué se guarda y cómo

Cada grabación crea una carpeta `capture/recordings/sesion_AAAAMMDD_HHMMSS/`.
El nombre de la carpeta usa la **hora local** de la laptop (sólo es un nombre);
los tiempos dentro de los archivos siempre son **UTC**.

| Archivo | Lo genera | Contenido |
| --- | --- | --- |
| `video.mp4` | `capture.py`, `detect.py` | Video original (códec mp4v). |
| `frames.csv` | ambos | **Hora UTC de cada fotograma.** Es la tabla clave para el GPS. |
| `session.json` | ambos | Metadatos de la sesión (cámara, resolución, fps, inicio/fin UTC…). |
| `annotated.mp4` | `detect.py` | Video con cajas, IDs y estelas dibujadas. |
| `detections.csv` | `detect.py` | Una fila por bache **y por fotograma**. |
| `tracks.csv` | `detect.py` | Una fila por bache único (resumen). |
| `crops/bache_NNNN.jpg` | `detect.py` | Recorte del mejor fotograma de cada bache. |

### 3.1 `frames.csv`

```csv
frame,t_rel_s,epoch_s,utc
0,0.0000,1788000000.1234,2026-10-26T14:30:00.123+00:00
1,0.0980,1788000000.2214,2026-10-26T14:30:00.221+00:00
```

| Columna | Significado |
| --- | --- |
| `frame` | Índice del fotograma, desde 0. Es el mismo índice que en `video.mp4`, `annotated.mp4` y `detections.csv`. |
| `t_rel_s` | Segundos desde que empezó la sesión. |
| `epoch_s` | Hora absoluta en segundos Unix (UTC). Útil para cálculos. |
| `utc` | La misma hora en ISO 8601 con milisegundos y zona `+00:00`. |

### 3.2 `session.json`

Campos: `camera` (`index`, `name`, `fourcc`), `video`, `frames_csv`,
`resolution` `[ancho, alto]`, `fps_nominal`, `fps_real`, `frames`, `duration_s`,
`start_utc`, `end_utc`, `clock_source` (siempre `"system"`) y, con `detect.py`,
un bloque `detection` con el modelo, `conf`, `imgsz`, `tracker`,
`tracks_total`, `baches_unicos` y `min_frames_valido`.

### 3.3 `detections.csv`

`frame, utc, track_id, clase, confianza, x1, y1, x2, y2` — caja en píxeles del
fotograma. `utc` es la misma hora que en `frames.csv` para ese `frame`.

### 3.4 `tracks.csv`

`track_id, clase, valido, frames, confianza_max, primer_frame, ultimo_frame,
primer_utc, ultimo_utc, mejor_frame, x1, y1, x2, y2, recorte`

- `track_id` es el ID del bache (1, 2, 3…) dentro de la sesión; **no** es único entre sesiones.
- `valido = 1` si se vio en al menos `--min-frames` fotogramas (filtra falsos positivos de 1–2 fotogramas).
- `mejor_frame` es el fotograma de mayor confianza; `x1..y2` es la caja en ese fotograma y `recorte` la ruta de su imagen.

## 4. Cómo se calculan los tiempos

Implementado en [capture/spm_capture/recorder.py](capture/spm_capture/recorder.py).

1. Al crear la sesión se toman dos relojes a la vez: `time.time()` (hora del
   sistema, `start_epoch`) y `time.perf_counter()` (reloj monotónico).
2. Cada fotograma lleva el instante en que se leyó de la cámara (`perf`).
3. `t_rel = perf − perf_inicio` y `hora_utc = start_epoch + t_rel`.

Por usar el reloj monotónico, los tiempos **no saltan** si Windows ajusta el
reloj a mitad de la grabación. La hora absoluta sólo depende de que el reloj de
la laptop estuviera bien **al iniciar** la sesión.

**Por qué se usa `frames.csv` y no `frame / fps`:** las cámaras USB no entregan
fps constantes, y en `detect.py` se descartan fotogramas cuando la inferencia es
más lenta que la cámara (`LatestFrameGrabber`). Por eso el video se escribe a los
fps *reales de procesamiento* (~10–13 en CPU), y el tiempo de reproducción del
video **no** equivale al tiempo real. La única referencia confiable es `frames.csv`.

### Limitaciones conocidas

- La hora depende del reloj de la laptop (`clock_source: "system"`). Si no se
  sincronizó, todo el video queda desfasado respecto al GPS.
- No se compensa la latencia propia de la cámara (exposición + USB), normalmente
  de decenas de ms. Se mide con la verificación del protocolo (sección 5).
- `start_epoch` se toma al crear la sesión, un instante antes de que el
  codificador de video abra el archivo (despreciable, milisegundos).

## 5. Protocolo de sincronización con el GPS (en campo)

1. Sincronizar la hora de la laptop (Windows: *Configuración → Hora e idioma →
   Sincronizar ahora*). El GPS toma la hora de los satélites.
2. Iniciar el GPS logger (smartphone o módulo) y esperar fix estable.
3. Iniciar la grabación (`capture.py` o `detect.py`).
4. **Verificación de desfase:** filmar unos segundos la pantalla del GPS logger
   mostrando su hora y compararla con la hora de ese fotograma en `frames.csv`.
   Si es mayor a ~0,5 s, anotarlo para corregirlo luego.
5. Al terminar, detener la grabación y luego el logger. Guardar el `.gpx` / `.csv`
   **dentro de la carpeta de la sesión**.

## 6. Cómo se va a guardar el GPS (Fase 5 — pendiente)

El GPS no se escribe durante la grabación: viene en un archivo `.gpx` aparte y
se une **después**, por hora UTC. El `.gpx` guarda puntos `<trkpt lat lon>` con
`<time>` en UTC, igual formato de hora que `frames.csv`, y por eso se pueden cruzar.

Algoritmo previsto (interpolación lineal, ver [fases.md](fases.md) Fase 5):

1. Por cada bache válido en `tracks.csv`, tomar la hora UTC de su `mejor_frame`
   (buscándola en `frames.csv` o en `detections.csv`).
2. En el `.gpx`, buscar los dos puntos que la rodean: `t0 ≤ t ≤ t1`.
3. Interpolar: `f = (t − t0) / (t1 − t0)`, `lat = lat0 + f·(lat1 − lat0)`, `lon` igual.
4. Guardar el resultado (lat/lon por bache) y mandarlo a la API.

Boceto (con `gpxpy`, aún no está en `requirements.txt` ni en el repo):

```python
import csv, gpxpy
from datetime import datetime

pts = [p for trk in gpxpy.parse(open("track.gpx")).tracks
         for seg in trk.segments for p in seg.points]

def position_at(t: datetime):
    for a, b in zip(pts, pts[1:]):
        if a.time <= t <= b.time:
            f = (t - a.time) / (b.time - a.time)
            return a.latitude + f * (b.latitude - a.latitude), \
                   a.longitude + f * (b.longitude - a.longitude)
    return None  # fuera del tramo con GPS

frames = {int(r["frame"]): r["utc"] for r in csv.DictReader(open("frames.csv"))}
for t in csv.DictReader(open("tracks.csv")):
    if t["valido"] == "1":
        utc = datetime.fromisoformat(frames[int(t["mejor_frame"])])
        print(t["track_id"], position_at(utc))
```

Notas para la implementación real: a 1 Hz del GPS y ~40 km/h el vehículo avanza
~11 m entre puntos, por eso interpolar y no tomar el punto más cercano; además
la posición del GPS es la del dispositivo, no la del bache (que está unos metros
adelante), lo que podría requerir un pequeño desplazamiento en la dirección de
marcha.

## 7. Cómo encaja con el backend

Cuando exista la Fase 5 completa, cada bache válido se enviaría a
`POST /api/baches/` ([API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)):

| Campo de la API | De dónde saldrá |
| --- | --- |
| `latitud`, `longitud` | Interpolación GPX (sección 6) |
| `timestamp_deteccion` | `utc` del `mejor_frame` |
| `confianza` | `confianza_max` de `tracks.csv` |
| `imagen` | `crops/bache_NNNN.jpg` |
| `gravedad` | Fase 4 (pendiente) |
| `radio_estimado` | Fase 4 (pendiente) |

## 8. Estructura del código de captura

```
capture/
├── capture.py              # Grabación de video + frames.csv + session.json
├── detect.py               # Lo anterior + detección YOLO + tracking
├── requirements.txt
├── README.md               # Guía rápida de uso
└── spm_capture/
    ├── cameras.py          # Listar/abrir cámaras (DirectShow en Windows); LatestFrameGrabber
    ├── recorder.py         # SessionRecorder (tiempos) y AsyncVideoWriter (video en hilo aparte)
    └── detection.py        # PotholeTracker (YOLO + ByteTrack) y DetectionLog (CSV, recortes)
```

El modelo provisional (YOLO11n, CC-BY-4.0, `tahaUgan/pothole-yolo11n`) se
descarga solo la primera vez en `capture/models/`.

## 9. Problemas comunes

- **No aparece la cámara:** probar otro puerto/cable USB (algunos solo cargan) y
  confirmar que esté en modo webcam/UVC.
- **"No se pudo abrir la cámara":** cerrar Zoom, Teams, el navegador o la app Cámara.
- **fps bajos:** poca luz sube la exposición y baja los fps; USB 2.0 limita la
  resolución sin MJPG. En `detect.py`, bajar `--imgsz`.
