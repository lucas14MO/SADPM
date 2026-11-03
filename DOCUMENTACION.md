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
| 4 | Clasificación de gravedad | ✅ Implementada en el pipeline: `pothole_light`, `pothole_moderate`, `pothole_critical` |
| 5 | Detección + tracking | ✅ En vivo (`capture/detect.py`) |
| 5 | **Georreferenciación offline (unir detecciones con GPS)** | ✅ Implementada en `capture/process_video.py` |
| 6 | Deduplicación espacial (DBSCAN) | ⏳ Pendiente |
| 7 | Backend Django REST | ✅ Hecho (`backend/`, ver [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)) |
| 8 | Frontend mapa (React + Leaflet) | ✅ Base hecha con datos mock (`frontend/`) |
| 9 | Integración end-to-end | ⏳ Pendiente |

> **Importante:** la captura no guarda coordenadas GPS en `video.mp4`; la Fase 5
> las asigna después mediante el `.gpx` y el timestamp UTC por fotograma de
> `frames.csv`.

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
`--out` (carpeta de salida; por defecto `capture/recordings`, pero puede
configurarse desde el flujo de captura o por otra parte del proyecto),
`--no-mjpg`.
Opciones de `detect.py`: `--model` (pesos `.pt`), `--conf` (default 0.3),
`--imgsz` (default 640), `--min-frames` (default 3, fotogramas mínimos para
considerar válido un bache), `--tracker` (`bytetrack.yaml` o `botsort.yaml`),
`--all-classes` (no filtrar sólo baches).

## 3. Qué se guarda y cómo

Cada grabación crea una carpeta de sesión bajo la ruta configurada por `--out`.
Por defecto, la salida es `capture/recordings/sesion_AAAAMMDD_HHMMSS/`, pero la
ubicación real puede depender del flujo de captura o de otra persona/componente
que defina la carpeta destino. El nombre de la carpeta usa la **hora local** de
la laptop (sólo es un nombre); los tiempos dentro de los archivos siempre son
**UTC**.

### 3.0 Clasificación de severidad de baches

El pipeline actual usa tres clases explícitas del modelo y de la exportación
offline:

| Clase del modelo | Severidad | Uso |
| --- | --- | --- |
| `pothole_light` | leve | daño pequeño o superficial |
| `pothole_moderate` | moderado | daño visible y más estructural |
| `pothole_critical` | crítico | grieta profunda/daño importante |

En la etapa offline, cada `track_id` se consolida por voto de clase y desempate
por confianza acumulada; la salida final usa la clase ganadora en
`severity` dentro de `processed_potholes.json`.

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

## 5. Procesamiento offline de Fase 5

Desde `capture/`, instalar `requirements.txt` y procesar una carpeta de sesión
con un modelo entrenado que contenga `pothole_light`, `pothole_moderate` y
`pothole_critical`:

```bash
python process_video.py recordings/sesion_AAAAMMDD_HHMMSS --model ../weights/weights.pt
```

La sesión requiere `video.mp4`, `frames.csv` y exactamente un `.gpx` (o se pasa
con `--gpx`). La inferencia recorre el video con ByteTrack (`persist=True`),
resume cada `track_id` por voto de clase y desempata por confianza agregada.
Solo se exportan tracks observados al menos `--min-frames` veces (default 3).
El keyframe es la observación de confianza máxima; su hora se toma de `frames.csv`
y se interpola linealmente en GPX. Fuera de la cobertura GPX se conservan el
bache y su evidencia, pero `latitude`/`longitude` son `null`.

La salida `processed_potholes.json` contiene una lista de objetos con
`track_id`, `severity`, `confidence_avg`, `confidence_max`, `latitude`,
`longitude`, `timestamp`, `frame_key`, `frames_detected`, `evidence_image`,
`location_method`, `vehicle_latitude`, `vehicle_longitude` y `projected_samples`.
Si la sesión tiene `camera_calibration.json`, `latitude`/`longitude` son la
posición del bache proyectada desde la cámara (ver sección 7).
Los recortes se guardan bajo `crops/`. Esta exportación local no realiza carga a
Django ni deduplicación espacial entre sesiones. El módulo de implementación y
opciones se documentan en [capture/README.md](capture/README.md).

## 6. Protocolo de sincronización con el GPS (en campo)

1. Sincronizar la hora de la laptop (Windows: *Configuración → Hora e idioma →
   Sincronizar ahora*). El GPS toma la hora de los satélites.
2. Iniciar el GPS logger (smartphone o módulo) y esperar fix estable.
3. Iniciar la grabación (`capture.py` o `detect.py`).
4. **Verificación de desfase:** filmar unos segundos la pantalla del GPS logger
   mostrando su hora y compararla con la hora de ese fotograma en `frames.csv`.
   Si es mayor a ~0,5 s, registrarlo como `--time-offset` en
   `calibrate_camera.py` (hora GPS − hora del equipo).
5. Al terminar, detener la grabación y luego el logger. Guardar el `.gpx` / `.csv`
   **dentro de la carpeta de la sesión**.

## 7. Cómo se guarda el GPS (Fase 5)

El GPS no se escribe durante la grabación: viene en un archivo `.gpx` aparte y
se une **después**, por hora UTC. El `.gpx` guarda puntos `<trkpt lat lon>` con
`<time>` en UTC, igual formato de hora que `frames.csv`, y por eso se pueden cruzar.

El procesador offline implementa interpolación lineal para el keyframe de mayor
confianza de cada track válido:

1. Por cada `track_id` con suficientes observaciones, tomar el timestamp UTC del
   frame con confianza máxima, consultándolo en `frames.csv`.
2. En el `.gpx`, buscar los dos puntos que la rodean: `t0 ≤ t ≤ t1`.
3. Interpolar: `f = (t − t0) / (t1 − t0)`, `lat = lat0 + f·(lat1 − lat0)`, `lon` igual.
4. Guardar lat/lon en `processed_potholes.json`; si el timestamp queda fuera del
   tramo GPS, se guardan como `null`.

La implementación está en `capture/spm_capture/offline.py`, usa `gpxpy` y se
invoca con el comando documentado en la sección 5.

A 1 Hz del GPS y ~40 km/h el vehículo avanza ~11 m entre puntos, por eso se
interpola y no se toma el punto más cercano.

### Compensación del offset de cámara

La posición del GPS es la de la antena, no la del bache, que se ve varios metros
adelante. Con una calibración de cámara (`camera_calibration.json`, generada con
`capture/calibrate_camera.py`) el procesador corrige la posición:

1. Cada observación del track se proyecta sobre la calzada con un modelo pinhole
   de suelo plano: el centro de la caja `(u, v)`, la altura del lente, la
   inclinación (`pitch`) y el campo de visión dan la distancia adelante/derecha
   desde la cámara; se suma el offset de montaje cámara–antena.
2. El rumbo del vehículo se calcula del propio GPX (posiciones interpoladas en
   `t ± 1 s`, ampliando la ventana si se movió menos de 2 m).
3. El desplazamiento se rota según el rumbo y se suma a la posición de la antena
   en ese instante (`t + time_offset_s`).
4. La posición final es el promedio ponderado por `1 / (h² + d²)`: el error de
   la proyección crece con el cuadrado de la distancia, así que las
   observaciones cercanas pesan más. Se descartan las proyecciones más allá de
   `max_distance_m` (30 m) y se prefieren las cajas que no tocan el borde.

Si no hay calibración, rumbo (vehículo detenido) o ninguna proyección válida,
se usa la posición del GPS como antes (`location_method = "gps_vehicle"`).

## 8. Integración futura con el backend

La exportación actual no llama a la API. Una futura ingesta a
`POST /api/baches/` ([API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)) deberá
mapear las clases del modelo a los valores aceptados por Django (`leve`,
`moderado`, `critico`) y omitir o resolver los baches sin coordenadas:

| Campo de la API | De dónde saldrá |
| --- | --- |
| `latitud`, `longitud` | Interpolación GPX (sección 6) |
| `timestamp_deteccion` | `utc` del `mejor_frame` |
| `confianza` | `confianza_max` de `tracks.csv` |
| `imagen` | `crops/bache_NNNN.jpg` |
| `gravedad` | Mapear `pothole_light/moderate/critical` a `leve/moderado/critico` |
| `radio_estimado` | Fase 4 (pendiente) |

## 9. Estructura del código de captura

```
capture/
├── capture.py              # Grabación de video + frames.csv + session.json
├── detect.py               # Lo anterior + detección YOLO + tracking
├── process_video.py        # Procesamiento offline + GPX + JSON
├── requirements.txt
├── README.md               # Guía rápida de uso
└── spm_capture/
    ├── cameras.py          # Listar/abrir cámaras (DirectShow en Windows); LatestFrameGrabber
    ├── recorder.py         # SessionRecorder (tiempos) y AsyncVideoWriter (video en hilo aparte)
      ├── detection.py        # PotholeTracker (en vivo) y DetectionLog
      └── offline.py         # Tracking batch, interpolación GPX y exportación JSON
```

El modelo provisional (YOLO11n, CC-BY-4.0, `tahaUgan/pothole-yolo11n`) se
descarga solo la primera vez en `capture/models/`.

## 10. Problemas comunes

- **No aparece la cámara:** probar otro puerto/cable USB (algunos solo cargan) y
  confirmar que esté en modo webcam/UVC.
- **"No se pudo abrir la cámara":** cerrar Zoom, Teams, el navegador o la app Cámara.
- **fps bajos:** poca luz sube la exposición y baja los fps; USB 2.0 limita la
  resolución sin MJPG. En `detect.py`, bajar `--imgsz`.
