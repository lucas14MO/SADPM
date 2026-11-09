# Guía del pipeline SADPM: orden de ejecución y umbrales

## 1. Orden del pipeline

### Paso 0 — Una vez por cada montaje de cámara

`capture/calibrate_camera.py` genera `capture/camera_calibration.json`: altura de
la cámara, inclinación y campo de visión. Repetir si se mueve la cámara.

### Paso 1 — En el recorrido

1. Arrancar el GPS Logger del celular (GPX) **antes** de grabar. Si el GPX
   empieza después, los primeros segundos quedan sin coordenadas.
2. Grabar con `capture/capture.py`:
   ```
   cd capture
   python capture.py --list
   python capture.py --camera N --record
   ```
   Cada sesión crea `recordings/sesion_AAAAMMDD_HHMMSS/` con `video.mp4`,
   `frames.csv` y `session.json`.

### Paso 2 — Copiar el GPX a la carpeta de la sesión

Copiar el `.gpx` dentro de cada `recordings/sesion_.../`. Si no está (o hay más
de uno), `process_video.py` falla y hay que pasarlo con `--gpx ruta/al/track.gpx`.

### Paso 3 — Detectar y ubicar los baches

```
cd capture
python process_video.py recordings/sesion_X --calibration camera_calibration.json
```

- Usa el modelo V4 (`weights/weights_v4_monoclass.pt`) por defecto.
- No usar `weights/weights.pt` (V3, tres clases): el pipeline lo rechaza.
- Genera `processed_potholes.json` y la carpeta `crops/` dentro de la sesión.

### Paso 4 — Levantar la base de datos y la API

**Windows (Django en Docker, recomendado):**
```
cd backend
docker compose --profile django up -d --build postgis django
```
Aplica las migraciones al arrancar y deja la API en `http://127.0.0.1:8000/api`.

**Linux con GDAL instalado (Django en el host):**
```
cd backend
docker compose up -d postgis
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

No usar las dos formas a la vez: ambas ocupan el puerto 8000.

### Paso 5 — Importar las sesiones

Una vez por sesión. Se puede repetir sin duplicar nada.

**Windows (PowerShell, desde `backend/`):**
```powershell
$SESION = "sesion_AAAAMMDD_HHMMSS"
docker compose run --rm -v "${PWD}\..\capture\recordings\${SESION}:/data/${SESION}:ro" `
  django python manage.py import_processed_potholes /data/$SESION
```

**Linux (Django en el host):**
```
python manage.py import_processed_potholes ../capture/recordings/sesion_AAAAMMDD_HHMMSS
```

Importante: montar la carpeta **con su mismo nombre** (`/data/$SESION`). El
nombre forma parte de la clave de sesión; si se monta con otro nombre (por
ejemplo `/data/session`), la sesión se registra dos veces.

### Paso 6 — Abrir el mapa

1. Crear `frontend/.env.local`:
   ```
   VITE_USE_MOCK_DATA=false
   VITE_API_BASE_URL=http://127.0.0.1:8000/api
   ```
2. Ejecutar:
   ```
   cd frontend
   npm install
   npm run dev
   ```
3. Abrir `http://127.0.0.1:5173`.

### Opcional — Detección en vivo

`capture/detect.py` detecta en vivo durante la grabación, pero con otro modelo
(YOLO11n). El pipeline de arriba no lo necesita.

---

## 2. Umbrales

### Detección y severidad

Definidos en `capture/spm_capture/offline.py` (clase `SeverityConfig`, líneas
24–30). Se cambian sin tocar el código, con opciones de `process_video.py`:

| Opción | Default | Qué hace |
| --- | --- | --- |
| `--conf` | 0.3 | Confianza mínima de YOLO. Más alto: menos falsos positivos, pero se escapan más baches. |
| `--min-frames` | 3 | Cantidad mínima de frames en que debe aparecer un bache para guardarlo. |
| `--roi-horizon` | 0.45 | Descarta detecciones cuyo centro esté en el 45 % superior de la imagen (cielo, edificios). |
| `--area-light` | 0.001 | Límite entre leve y moderado, sobre el área relativa del bache (`area_norm`). |
| `--area-critical` | 0.005 | Límite entre moderado y crítico. |
| `--perspective-reference-y` | 0.7 | Fila de la imagen (fracción de la altura) usada como referencia para corregir la perspectiva. |
| `--perspective-exponent` | 2.0 | Cuánto agranda la corrección los baches lejanos. |

Ejemplo:
```
python process_video.py recordings/sesion_X --calibration camera_calibration.json \
  --conf 0.5 --area-light 0.0008 --area-critical 0.003
```

**Cómo calibrar la severidad:** importa las sesiones y abre la pestaña
**Calibración** del frontend conectado a la API. Inicia sesión en `/admin/` con
una cuenta staff, clasifica los recortes y descarga el CSV con `area_norm` y la
clase humana. Con esos datos, define los límites entre grupos.

Para aplicar umbrales nuevos a la base sin volver a procesar videos, prueba
primero con `--dry-run` y luego ejecuta:

```
cd backend
python manage.py recalcular_severidad \
   --light-threshold 0.001 --critical-threshold 0.005 --dry-run
python manage.py recalcular_severidad \
   --light-threshold 0.001 --critical-threshold 0.005
```

El comando actualiza observaciones con `area_norm` y reconstruye consolidados;
no modifica baches manuales ni observaciones sin área. En el siguiente proceso
offline, pasa también esos valores con `--area-light` y `--area-critical` para
que las nuevas observaciones usen la misma calibración.

### Agrupación de duplicados (backend)

- `--eps-meters` (default 2.5) en `import_processed_potholes`: detecciones a
  menos de esa distancia se cuentan como el mismo bache.
  Definido en `backend/potholes/management/commands/import_processed_potholes.py:33`.

### Ocultar baches por feedback (backend)

- Un bache se oculta con **3 reportes de falso positivo** o **1 de reparado**.
- Fijo en código: `backend/potholes/views.py:89`. No hay opción para cambiarlo.
