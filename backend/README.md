# Backend y base espacial SPM

En desarrollo, PostGIS corre en Docker Compose y Django corre directamente en el
host usando el entorno Python del repositorio. Esto permite depurar Django desde
VS Code; PostgreSQL solo se publica en loopback (`127.0.0.1`).

## Iniciar PostGIS y Django local

```bash
cd backend
cp .env.example .env
# Cambia POSTGRES_PASSWORD en .env para tu entorno local.
```

En Void Linux, instala las bibliotecas nativas que GeoDjango carga (`libgdal`,
GEOS y PROJ). Los paquetes `-devel` también se incluyen por si alguna dependencia
Python necesita compilar extensiones:

```bash
sudo xbps-install -S libgdal libgdal-devel geos geos-devel proj proj-devel
```

El entorno Python del repositorio está en `../.venv`. Actívalo desde `backend/`
para que el intérprete use su ruta canónica:

```bash
source ../.venv/bin/activate
python -m pip install -r requirements.txt
sudo docker compose up -d postgis
sudo docker compose ps
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

El comando `runserver` ocupa la terminal. Déjalo abierto mientras uses la API;
deténlo con `Ctrl+C`. `backend/.env` debe tener `POSTGRES_HOST=127.0.0.1` y
`POSTGRES_PORT=5432`, además de las mismas credenciales que usa el servicio
`postgis` de Compose. La plantilla `.env.example` contiene estos campos. Si
`DJANGO_PORT` en `.env` no es `8000`, reemplaza el puerto del último comando por
ese valor.

### Alternativa: Django en Docker (Windows o sin GDAL local)

GeoDjango necesita GDAL/GEOS/PROJ nativos, difíciles de instalar en Windows. El
servicio `django` de Compose (perfil opcional `django`) los trae en la imagen,
aplica las migraciones al arrancar y guarda la evidencia en el volumen
`media_data`:

```bash
docker compose --profile django up -d --build postgis django
docker compose ps
```

No ejecutes a la vez `runserver` en el host: ambos publican `DJANGO_PORT`.
Sin `--profile django`, `docker compose up -d postgis` funciona como antes.

Para levantar también el frontend en Docker:

```bash
sudo docker compose up -d --build --remove-orphans postgis frontend
```

Vite queda en `http://127.0.0.1:5173` y consulta Django en
`http://127.0.0.1:${DJANGO_PORT:-8000}/api`. El servicio `django` solo se
levanta con el perfil `django` (ver arriba). El volumen `postgis_data` conserva la base; no ejecutes
`docker compose down -v`.

Django ejecutado en el host guarda nuevas imágenes en `backend/media/`. Si la
instalación anterior ya guardó imágenes en el volumen Docker `media_data`, esas
imágenes no aparecen automáticamente en la carpeta local; cópialas antes de
depender de los registros existentes que las referencian.

Verifica la API en `http://127.0.0.1:${DJANGO_PORT:-8000}/api/baches/`.

Las migraciones habilitan PostGIS, crean las tablas de sesiones/observaciones,
conservan las coordenadas del modelo existente y agregan índices espaciales.
Los baches creados antes de esta migración conservan su PK y no se convierten en
observaciones ni se incluyen automáticamente en deduplicación; siguen siendo
registros manuales/no gestionados.

## Importar una sesión y consolidar baches

El procesador offline de `capture/` produce `processed_potholes.json` y recortes.
Importa una carpeta de sesión así:

Con Django en el host:

```bash
python manage.py import_processed_potholes ../capture/recordings/sesion_AAAAMMDD_HHMMSS
python manage.py import_processed_potholes ../capture/recordings/sesion_AAAAMMDD_HHMMSS \
  --eps-meters 2.5
```

Con Django en Docker (perfil `django`), montando la sesión con **su mismo nombre**:

```bash
SESION=sesion_AAAAMMDD_HHMMSS
sudo docker compose run --rm \
  -v "$(realpath ../capture/recordings/$SESION):/data/$SESION:ro" \
  django python manage.py import_processed_potholes /data/$SESION
```

En PowerShell:

```powershell
$SESION = "sesion_AAAAMMDD_HHMMSS"
docker compose run --rm -v "${PWD}\..\capture\recordings\${SESION}:/data/${SESION}:ro" `
  django python manage.py import_processed_potholes /data/$SESION
```

Sustituye `sesion_AAAAMMDD_HHMMSS` por el directorio real de la sesión. El nombre
de la carpeta forma parte de la clave de sesión: si la misma sesión se importa
desde carpetas con nombres distintos (por ejemplo, montándola como
`/data/session`), se registra dos veces.

La importación es idempotente por nombre/inicio de sesión y `track_id`. Conserva
observaciones originales, actualiza esa sesión y recalcula los baches consolidados
entre recorridos mediante `ST_ClusterDBSCAN`. Las distancias se calculan en UTM
21S (EPSG:32721), adecuado a la zona de Encarnación. El radio inicial de
agrupación es 2.5 m y cada observación georreferenciada crea un grupo aunque esté
aislada. Las observaciones con coordenadas nulas se guardan, pero no se agrupan.
Cada observación conserva severidad canónica, confianza promedio/máxima,
`area_norm`, cantidad de frames, timestamp, keyframe y ruta local de evidencia.
Durante la importación, los recortes se copian al almacenamiento persistente
`MEDIA`; la ruta montada de la sesión no se usa como URL pública. El agregador
asocia al bache consolidado la evidencia del registro representativo.
Para identificar la sesión usa `session.json.start_utc` o el primer timestamp de
`frames.csv`; así la clave no depende de la ruta absoluta de la carpeta. Si se
mueve una sesión, conserva su nombre y sus timestamps para que se reconozca como
la misma importación.
La identidad de cada consolidado se deriva del conjunto de IDs de observación;
si una recomputación deja iguales sus miembros, conserva la PK del bache. Cuando
los miembros cambian, se actualizan las agrupaciones afectadas y se retiran solo
los consolidados que ya no representan ningún grupo.

La API conserva el contrato de baches existente. Las consultas de radio utilizan
`ST_DWithin` sobre geography y reciben el radio en metros. Las observaciones y
consolidados se administran por Django; no se añade un endpoint de ingesta en
esta fase.

## Clasificación y recalibración de severidad

Aplica las migraciones y crea una cuenta interna con permisos de staff:

```bash
python manage.py migrate
python manage.py createsuperuser
```

En el frontend conectado a esta API, inicia sesión en `/admin/` con esa cuenta y
abre la pestaña **Calibración**. La pantalla permite etiquetar observaciones con
recorte y `area_norm`; guarda la etiqueta humana separada de la severidad
calculada y descarga las etiquetas guardadas como CSV. El listado y la
actualización requieren una sesión Django autenticada y un usuario `is_staff`.

Para cambiar los umbrales de observaciones ya importadas, sin reejecutar videos:

```bash
python manage.py recalcular_severidad \
  --light-threshold 0.001 \
  --critical-threshold 0.008 \
  --dry-run
python manage.py recalcular_severidad \
  --light-threshold 0.001 \
  --critical-threshold 0.008
```

Con Django en Docker (perfil `django`), los mismos comandos se ejecutan dentro
del contenedor:

```bash
docker compose exec django python manage.py createsuperuser
docker compose exec django python manage.py recalcular_severidad \
  --light-threshold 0.001 --critical-threshold 0.008
```

El umbral leve debe ser positivo y menor que el crítico. El comando actualiza
observaciones con `area_norm`, reconstruye los baches consolidados y conserva
feedback; deja intactos los baches manuales y observaciones sin área. `--eps-meters`
permite cambiar el radio de agrupación (default 2.5 m). En desarrollo, los
orígenes frontend confiables para CSRF se configuran con
`DJANGO_CSRF_TRUSTED_ORIGINS`.

El endpoint `POST /api/baches/{id}/feedback/` recibe `feedback_type`
(`false_positive` o `repaired`) y un UUID anónimo del cliente. El mismo token no
puede votar más de una vez por tipo y bache. Tres reportes de falso positivo o
uno de reparación ocultan el bache de consultas públicas. Los reportes se
reasocian a los clusters reconstruidos según el mayor solapamiento de sus
observaciones.

## Respaldo

Crear un respaldo SQL comprimido:

```bash
sudo docker compose exec -T postgis sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

Restaurarlo en una base ya creada:

```bash
gzip -dc backup.sql.gz | sudo docker compose exec -T postgis sh -c \
  'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

No uses `docker compose down -v` salvo que quieras eliminar deliberadamente el
volumen y todos los datos persistidos.