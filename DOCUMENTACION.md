# SAD Pothole Map (SPM) — Documentación técnica del estado actual

Este documento describe lo que **ya está implementado** y cómo se relacionan los
tiempos (timestamps) del video con el GPS. Para el plan completo ver [fases.md](fases.md).

## 1. Estado por fase

| Fase | Qué es | Estado |
| --- | --- | --- |
| 1 | Captura de video + timestamps por fotograma | ✅ Hecho (`capture/capture.py`) |
| 1 | Captura del GPS (`.gpx`) | ✅ Externo: aplicación de iOS que exporta el recorrido en GPX (sección 11); **no hay código** |
| 2 | Dataset y etiquetado | ✅ V4: 386 imágenes (143 propias, 243 de un *fork* público), split 71/19/10, CC BY 4.0 |
| 3 | Entrenamiento propio | ✅ V4 YOLO26 Small monoclass (Roboflow iteración 9, AGPL-3.0). Test: P 76,3 %, R 64,3 %, F1 69,8 %, mAP@50 60,8 % (ver [IA_Models.md](weights/IA_Models.md)) |
| 4 | ROI de asfalto y severidad por área relativa | ✅ Implementado; umbrales calibrados (`0.001`/`0.008`) con la pestaña Calibración; ROI y perspectiva provisionales |
| 5 | Detección + tracking | ✅ En vivo (`capture/detect.py`, V4) y offline (`process_video.py`, V4 + ByteTrack) |
| 5 | **Georreferenciación offline (unir detecciones con GPS)** | ✅ Implementada en `capture/process_video.py` |
| 6 | Deduplicación espacial (DBSCAN) | ✅ Implementada al importar/reconstruir en Django/PostGIS (`eps=2.5 m` inicial) |
| 7 | Backend Django REST | ✅ Importación, evidencia, feedback, clasificación por staff y `recalcular_severidad`; migraciones 0001–0004 aplicadas en PostGIS (Docker) |
| 8 | Frontend mapa (React + Leaflet) | ✅ Búsqueda por radio, visor de evidencia, feedback con opacidad por votos, modal **Votos** y pestaña **Calibración**; build OK y conectado a la API real |
| 9 | Integración end-to-end | ⚠️ Probada con 403 fotogramas + GPX del 7/11 (89 baches en el mapa); falta un recorrido completo en video a 30 fps |

> **Importante:** la captura no guarda coordenadas GPS en `video.mp4`; la Fase 5
> las asigna después mediante el `.gpx` y el timestamp UTC por fotograma de
> `frames.csv`.

### Criterio implementado y validación pendiente

El procesamiento offline usa YOLO como detector monoclass (`pothole`) y fuente
de confianza; ROI y severidad se calculan después con reglas deterministas.
Los valores actuales son configurables y provisionales: la lógica tiene pruebas
sintéticas, pero aún no se calibró ni validó con una sesión visual completa.

- **ROI del asfalto:** para una imagen de ancho `W` y alto `H`, calcular el
   centroide vertical `Y_center = (y1 + y2) / 2` de cada caja y descartar la
   detección si `Y_center < 0.45 × H`. El límite es inicial y configurable; la
   ROI debe validarse para el encuadre real de cada montaje.
- **Severidad por área:** calcular `A = (x2 - x1) × (y2 - y1)` y
   `A_norm = A / (W × H) × f(Y_center)`. El procesador actual usa
   `f(y) = ((y_ref-y_roi)/(y-y_roi))^p`, limitado cerca del horizonte; `y_ref`,
   `y_roi` y `p` son configurables y requieren calibración por montaje.
- **Keyframe:** calcular la severidad sobre un keyframe representativo del
   track: mayor área de caja dentro de la ROI, desempate por confianza. Severidad,
   crop anotado, timestamp y posición usan la misma observación.
- **Mapeo:** `A_norm < Umbral_Leve` produce `leve`; entre `Umbral_Leve` y
   `Umbral_Crítico`, `moderado`; desde `Umbral_Crítico`, `critico`. Los umbrales
   se calibran con la pestaña **Calibración** del frontend y se aplican a la
   base con `recalcular_severidad` (ver [PIPELINE.md](PIPELINE.md)). Defaults
   actuales: umbrales `0.001`/`0.008` (calibración del equipo del 9/11/2026);
   ROI `0.45`, referencia `0.7` y exponente `2.0` siguen siendo provisionales.
   La confianza del modelo se conserva como dato separado de la severidad.
- **Evidencia y feedback:** el detalle del mapa mostrará el recorte del keyframe
   con su caja dibujada y permitirá reportar falso positivo o bache
   reparado/desactualizado. El objetivo backend es ocultar o marcar inválido un
   bache con al menos 3 reportes de falso positivo, o un reporte de
   reparado/desactualizado. Backend y UI ya incluyen persistencia/endpoint y
   controles idempotentes por UUID de navegador. Los conteos se calculan desde
   feedback persistido, se refrescan en los clientes y modulan la opacidad; el
   modal **Votos** lista también los baches ocultos. El flujo de UI debe probarse
   integrado.

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

El flujo en vivo usa por defecto el mismo modelo V4 monoclass que el
procesamiento offline (`weights/weights_v4_monoclass.pt`). Como detecta y graba
en el mismo bucle, el video queda por debajo de 30 fps en CPU; los recorridos
para `process_video.py` se graban con `capture.py`.

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

### 3.0 Compatibilidad con el modelo V3 multiclase

El modelo anterior V3 (`weights/weights.pt`) predice tres clases explícitas:

| Clase del modelo | Severidad | Uso |
| --- | --- | --- |
| `pothole_light` | leve | daño pequeño o superficial |
| `pothole_moderate` | moderado | daño visible y más estructural |
| `pothole_critical` | crítico | grieta profunda/daño importante |

Las sesiones V3 existentes conservan etiquetas legacy y el importador las
mapea a severidades canónicas. El procesamiento offline actual usa V4
monoclass; la severidad exportada (`leve`, `moderado`, `critico`) no procede de
la clase YOLO.

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
con el modelo YOLO26 Small monoclass V4 (`pothole`):

```bash
python process_video.py recordings/sesion_AAAAMMDD_HHMMSS
```

La sesión requiere `video.mp4`, `frames.csv` y exactamente un `.gpx` (o se pasa
con `--gpx`). La inferencia usa ByteTrack (`persist=True`) y la clase `pothole`.
Descarta centros por encima del horizonte ROI y exige al menos `--min-frames`
observaciones válidas (default 3). Selecciona la caja de mayor área y desempata
por confianza; calcula severidad mediante `A_norm`, con parámetros configurables
en CLI cuyos defaults aún son provisionales. El timestamp de ese keyframe se
toma de `frames.csv` y se interpola linealmente en GPX. Fuera de la cobertura GPX
se conserva el bache y evidencia, con `latitude`/`longitude` en `null`.

La salida `processed_potholes.json` contiene una lista de objetos con
`track_id`, severidad canónica, `area_norm`, `confidence_avg`, `confidence_max`,
`confidence_keyframe`, `latitude`, `longitude`, `timestamp`, `frame_key`,
`frames_detected`, `evidence_image`, `location_method`, `vehicle_latitude`,
`vehicle_longitude` y `projected_samples`.
Si la sesión tiene `camera_calibration.json`, `latitude`/`longitude` son la
posición del bache proyectada desde la cámara (ver sección 7).
Los recortes anotados se guardan como `crops/bache_NNNN.jpg`. La exportación
local no llama la API; el comando Django importa la sesión, copia evidencia a
MEDIA y reconstruye la deduplicación espacial. El módulo de implementación y
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
área de caja dentro de la ROI (desempate por confianza) de cada track válido:

1. Por cada `track_id` con suficientes observaciones, tomar el timestamp UTC del
   frame seleccionado por área máxima, consultándolo en `frames.csv`.
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
4. Se usa la proyección del keyframe representativo para mantener coordenada,
   severidad, evidencia y timestamp asociados a la misma observación. Se
   descartan proyecciones más allá de `max_distance_m` (30 m); si el keyframe no
   tiene proyección válida se recurre a la posición del GPS (`gps_vehicle`).

Si no hay calibración, rumbo (vehículo detenido) o ninguna proyección válida,
se usa la posición del GPS como antes (`location_method = "gps_vehicle"`).

## 8. Importación al backend

La exportación local no llama directamente a la API. La importación implementada
se hace con el comando `import_processed_potholes` documentado en
[`backend/README.md`](backend/README.md): valida severidad canónica V4 y las
etiquetas legacy V3, conserva observaciones, copia imágenes a MEDIA y reconstruye
los baches consolidados. Las detecciones sin coordenadas se conservan como
observaciones, pero no aparecen en el clustering espacial. El endpoint público se describe en
[`API_DOCUMENTATION.md`](backend/API_DOCUMENTATION.md).

El modelo incorpora `area_norm`, evidencia persistente, contadores y visibilidad.
La API acepta feedback idempotente por bache/tipo/UUID; 3 reportes de falso
positivo o uno de reparación ocultan el bache. La migración `0003` está aplicada
en la base PostGIS del entorno de desarrollo; los tests backend usan una base
temporal.

Los contadores públicos se derivan de los votos guardados, así que los clientes
comparten el mismo conteo. El mapa usa el total de reportes para bajar
progresivamente la opacidad y refresca al volver a la pestaña o cada 15 segundos.
El botón **Votos** abre el listado de baches reportados, incluidos los que ya no
son visibles en el mapa. Para simular votos desde desarrollo, agrega registros
en el inline **Feedbacks** de un bache en Django Admin; el conteo y la
visibilidad se recalculan al guardar. Ver [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)
y [backend/README.md](backend/README.md) para los endpoints y el procedimiento.

| Campo de la API | De dónde saldrá |
| --- | --- |
| `latitud`, `longitud` | Interpolación GPX (sección 6) |
| `timestamp_deteccion` | `utc` del keyframe de mayor área dentro de ROI |
| `confianza` | `confianza_max` de `tracks.csv` |
| `imagen` | `crops/bache_NNNN.jpg` |
| `gravedad` | Severidad determinista de `area_norm`; las etiquetas V3 se admiten por compatibilidad |
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

El flujo en vivo `detect.py` y el procesamiento offline usan por defecto el
mismo modelo, `../weights/weights_v4_monoclass.pt` (o el indicado con
`--model`; en offline debe tener la única clase `pothole`).

## 10. Problemas comunes

- **No aparece la cámara:** probar otro puerto/cable USB (algunos solo cargan) y
  confirmar que esté en modo webcam/UVC.
- **"No se pudo abrir la cámara":** cerrar Zoom, Teams, el navegador o la app Cámara.
- **fps bajos:** poca luz sube la exposición y baja los fps; USB 2.0 limita la
  resolución sin MJPG. En `detect.py`, bajar `--imgsz`.

## 11. Guía de montaje y registro de campo

### Procedimiento utilizado en la campaña del 7/11/2026

La captura de campo se realizó en Encarnación con el siguiente procedimiento:

- **Vehículo y equipo humano:** un automóvil con dos integrantes del equipo; uno
  conducía y el otro, en el asiento del acompañante, operaba el sistema de
  captura.
- **Equipo de captura:** cámara conectada a una laptop con `capture.py` en
  ejecución. El operador iniciaba y detenía cada sesión desde la laptop.
- **Calibración previa:** antes de grabar, con el vehículo detenido, se calibró
  la cámara sobre el asfalto con `calibrate_camera.py`. El resultado está en
  `capture/camera_calibration.json`: altura de 1,35 m, inclinación de 1,462° y
  campo de visión horizontal de 118,15°.
- **GPS:** el recorrido se registró con una aplicación de iOS que lo exporta en
  formato GPX (`capture/gpx/07-nov-2026-1750.gpx`: 418 puntos, de 20:40:30 a
  20:49:50 UTC). La calibración registra un desplazamiento nulo entre la cámara
  y el teléfono (`forward_offset_m` y `right_offset_m` en 0).
- **Resultado:** cinco sesiones de video (de 20:39 a 20:49 UTC). La primera,
  `sesion_20261107_173925`, comenzó antes que el registro GPS y quedó sin
  coordenadas; por eso el registro GPS debe iniciarse antes que la grabación.

Datos que conviene completar en la ficha de campo: nombre y versión de la
aplicación de iOS, frecuencia de registro, modelo de cámara y posición del
teléfono dentro del vehículo.

### Recomendaciones generales

Registrar en cada campaña las medidas del vehículo, la cámara y el registrador
GPS; no asumir como medidas reales los valores de ejemplo del calibrador.

### Montaje y calibración de cámara

Fijar la cámara mirando al frente, centrada y rígida para evitar vibración y
cambios de inclinación. Evitar que el soporte obstruya la calzada. Medir desde
la calzada hasta el centro del lente (`camera_height_m`), la posición de cámara
respecto a la antena GPS (`forward_offset_m`, `right_offset_m`), el giro lateral
(`yaw`) y la inclinación hacia abajo (`pitch`). Registrar resolución, lente/FOV,
vehículo y fotos del montaje. Estos son parámetros medidos en campo, no valores
universales.

Calibrar en suelo plano con marcadores a distancias conocidas y el vehículo
detenido. Seguir los ejemplos de `capture/calibrate_camera.py`; guardar la salida
como `capture/camera_calibration.json`, revisar la grilla de distancias con
`--check` y confirmar que la sesión copie la calibración. Medir también el
desfase horario de cámara/GPS y pasarlo como `--time-offset` (hora GPS menos
hora del equipo). Validar luego la ubicación proyectada contra puntos conocidos.

### GPS Logger y sincronización

El proyecto no fija una app/dispositivo GPS Logger ni sus ajustes: confirmar y
anotar en la hoja de campo el nombre y versión, dispositivo, formato GPX, zona
horaria UTC, frecuencia de registro, modo de precisión/alta exactitud, permisos
de ubicación y si el registro continúa con pantalla apagada. Mantener activados
los servicios de ubicación y esperar un fix estable antes de iniciar el vídeo.
El pipeline espera timestamps GPX con zona horaria y une por UTC.

Antes de grabar, sincronizar el reloj del equipo, iniciar el logger y registrar
unos segundos su reloj visible en el video. Grabar la ruta; al terminar, detener
ambos y copiar exactamente un `.gpx` a la carpeta de sesión. Si se detecta
desfase, documentarlo y configurar la calibración. Revisar cobertura GPX y
`frames.csv` antes de importar.

### Procedimiento de demo y uso

1. Preparar entorno de captura e identificar cámara con `python capture.py --list`.
2. En recorrido controlado, iniciar el GPX **antes** que el video/detección (si el
   GPX empieza después, los primeros segundos quedan sin coordenadas); conservar
   la carpeta completa de sesión y copiar el `.gpx` dentro de ella (o pasarlo con
   `--gpx`).
3. Procesar desde `capture/` con el modelo V4 monoclass documentado en
   [IA_Models.md](weights/IA_Models.md), que es el predeterminado:
   `python process_video.py recordings/<sesion> --calibration camera_calibration.json`.
   El modelo V3 (`weights.pt`, tres clases) ya no es compatible con este paso.
4. Revisar `processed_potholes.json`, recortes, coordenadas y cobertura temporal.
5. Iniciar PostGIS/API según [backend/README.md](backend/README.md) e importar la
   sesión con `import_processed_potholes` (incluyendo el volumen de solo lectura
   como allí se indica). Mostrar el número importado y consolidado.
6. Abrir el mapa y verificar los baches de la API, severidad, ubicación y
   evidencia. El frontend usa datos mock si `VITE_USE_MOCK_DATA` no es `false`;
   configurar `VITE_API_BASE_URL` según el entorno.

Para cerrar la demo, registrar fecha, sesión usada, versión del modelo, parámetros
de procesamiento, resultado de importación, URL del mapa y limitaciones
observadas. La demo end-to-end todavía requiere ejecución y validación con datos
reales; esta guía describe el procedimiento, no afirma que ya se haya probado.
