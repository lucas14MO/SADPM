# Roadmap y Fases de Desarrollo - SAD Pothole Map (SPM)

> [!NOTE]
> **Aclaración Arquitectónica Principal**: El sistema procesa video grabado (modo offline / diferido). El concepto de "tiempo real" se refiere a la velocidad y eficiencia de procesamiento por fotograma del modelo (FPS sostenidos), lo cual elimina la necesidad de cómputo en vivo a bordo del vehículo y simplifica significativamente la arquitectura de despliegue.

## Stack Tecnológico Definido

| Capa | Tecnologías Seleccionadas |
| :--- | :--- |
| **Frontend** | React, Leaflet.js, React-Leaflet, Vanilla CSS / TailwindCSS |
| **Backend API** | Django, Django REST Framework (DRF), Python |
| **Base de Datos** | PostgreSQL + PostGIS (Soporte geoespacial nativo) |
| **IA & Visión por Computadora** | Python, Ultralytics YOLO26 (V4 monoclass), OpenCV, PyTorch, ByteTrack / BoT-SORT |
| **Geoprocesamiento & Datos** | Roboflow / CVAT, GPX Logger, DBSCAN (Scikit-Learn) |

---

## Fase 0 — Definición, Alcance y Arquitectura
- **Objetivo**: Establecer los criterios base del proyecto, delimitar zonas de estudio y formalizar el stack.
- **Entregables**:
  - Definición provisional de criterios de gravedad (Leve, Moderado, Crítico).
  - Delimitación geográfica de la zona de prueba (Rutas / Calles seleccionadas de Encarnación).
  - Asignación de roles de desarrollo (Datos/IA, Pipeline de Video/GPS, Backend Django + Frontend React).
  - Configuración inicial de repositorios y entornos virtuales en Python y Node.js.

## Fase 1 — Captura de Datos y Hardware en Campo
- **Objetivo**: Grabar secuencias de video de alta resolución y sus correspondientes trazados GPS.
- **Entregables & Tecnologías**:
  - Montaje de cámara / Smartphone en posición frontal sobre el vehículo.
  - Captura simultánea de video (`.mp4`) y trazados GPS (`.gpx` / `.csv`).
  - Protocolo de sincronización de marcas de tiempo (timestamps) entre cámara y GPS Logger.

## Fase 2 — Dataset, Etiquetado y Preprocesamiento de Imágenes
- **Objetivo**: Generar un conjunto de datos anotado en formato YOLO optimizado para entrenamiento.
- **Entregables & Tecnologías** (`OpenCV`, `Roboflow`, `CVAT`):
  - Extracción de fotogramas clave con OpenCV.
  - Filtrado de imágenes de baja calidad o desenfocadas (desenfoque laplaciano).
  - Etiquetado de cajas delimitadoras (bounding boxes) de baches.
  - Combinación con datasets públicos de baches (Roboflow Universe / Kaggle).
  - Aplicación de Data Augmentation y división del dataset (70% Train, 20% Val, 10% Test).

## Fase 3 — Entrenamiento y Evaluación del Modelo IA
- **Objetivo**: Obtener un detector de baches de alta precisión basado en YOLO.
- **Entregables & Tecnologías** (`Ultralytics YOLO26`, `PyTorch`):
  - Entrenamiento supervisado del modelo YOLO.
  - Evaluación cuantitativa con métricas `mAP@50`, `mAP@50-95`, `Precision`, `Recall`.
  - Ajuste fine-tuning e hiperparámetros.
  - Matriz de confusión y análisis de falsos positivos/negativos.

## Fase 4 — Clasificación de Gravedad y Lógica de Negocio
- **Estado**: ROI, fórmula configurable, umbrales y clasificación canónica implementados en el pipeline offline con defaults provisionales; calibración con datos etiquetados pendiente.
- **Objetivo**: Filtrar detecciones fuera de la calzada y asignar severidad de forma determinista con el área aparente del bache, sin depender de clases de severidad predichas por YOLO.
- **Entregables**:
  - Aplicar una región de interés (ROI) del asfalto. Como regla inicial, ignorar detecciones cuyo centroide vertical cumpla `Y_center < 0.45 × H`; validar y permitir ajustar el límite para el montaje real.
  - Calcular `A_norm = A / (W × H) × f(Y_center)`; el procesador usa una corrección de perspectiva configurable, con calibración por montaje pendiente.
  - Elegir como keyframe la mayor área de caja observada dentro de ROI y desempatar por confianza.
  - Clasificar el keyframe con umbrales configurables: `leve` por debajo de `Umbral_Leve`, `moderado` entre ambos umbrales y `critico` desde `Umbral_Crítico`. Calibrar los valores antes de usarlos como métricas de campo.
  - Mantener la presentación Verde (Leve), Amarillo (Moderado) y Rojo (Crítico), y documentar las limitaciones de estimar tamaño/severidad con cámara monocular.

## Fase 5 — Pipeline de Video, Tracking Temporal y Georreferenciación
- **Objetivo**: Procesar videos completos, rastrear baches cuadro a cuadro y asociar coordenadas GPS.
- **Entregables & Tecnologías** (`OpenCV`, `ByteTrack / BoT-SORT`, `gpxpy`):
  - Inferencia batch sobre video completo.
  - Tracking multi-objeto con ByteTrack para resumir detecciones por ID dentro de una sesión.
  - Aplicar el filtro ROI y la clasificación determinista por área normalizada al keyframe representativo de cada track; conservar la confianza YOLO como una métrica independiente.
  - Interpolación lineal del track GPX para asignar latitud/longitud al keyframe de mayor área dentro de ROI (desempate por confianza), usando timestamps UTC de `frames.csv`.
  - Exportar severidad canónica determinista, confianza, `area_norm` y ruta del recorte anotado a `processed_potholes.json` y `crops/bache_NNNN.jpg`.
- **Estado**: pipeline V4 monoclass, ROI, severidad configurable y exportación implementados; suite local de captura pasa. Defaults de perspectiva/umbrales son provisionales y falta validar con video/GPX/imágenes completos. La calibración geométrica requiere valores medidos para cada montaje.

## Fase 6 — Deduplicación Espacial
- **Objetivo**: Evitar registros duplicados de un mismo bache entre diferentes pasadas por la misma ruta.
- **Entregables & Tecnologías** (`DBSCAN / Scikit-Learn`, `PostGIS ST_ClusterDBSCAN`):
  - Clustering de coordenadas geográficas dentro de un umbral de proximidad (ej. 2 - 3 metros).
  - Consolidación del bache representativo (mejor nivel de confianza / foto más nítida).
- **Implementado**: PostgreSQL/PostGIS en contenedor, observaciones por sesión y comando `import_processed_potholes` desde `processed_potholes.json`; la importación reconstruye consolidados con `ST_ClusterDBSCAN`.
- **Criterio inicial**: `eps=2.5 m`, configurable; preservar observaciones originales y excluir del clustering las que no tienen coordenadas.

## Fase 7 — Backend REST API & Base de Datos Espacial (Django + PostgreSQL)
- **Estado**: modelos, migración, importación de evidencia y endpoint implementados; migración aplicada y suite backend validada con PostgreSQL/PostGIS.
- **Objetivo**: Desarrollar la infraestructura servidora para almacenamiento y consulta espacial de baches.
- **Entregables & Tecnologías** (`Django`, `Django REST Framework`, `PostgreSQL + PostGIS`):
  - Persistir por bache la geometría, severidad determinista (`leve`, `moderado`, `critico`), URL/archivo de evidencia, confianza YOLO, `area_norm`, timestamp y contadores de feedback ciudadano.
  - Endpoints REST para consulta geoespacial: baches por radio/bounding box.
  - Comando de importación de sesiones procesadas a la base espacial (`backend/potholes/management/commands/import_processed_potholes.py`). No es una carga HTTP a la API; la integración con el mapa/API debe configurarse y verificarse.
  - Endpoint para registrar votos de falso positivo y de bache reparado/desactualizado. Aplicar ocultamiento cuando haya al menos 3 reportes de falso positivo o un reporte de desactualización; limitar duplicados por UUID de cliente.
  - Excluir los baches invalidados/desactualizados de las consultas públicas del mapa y conservar su estado/contadores para auditoría.

## Fase 8 — Frontend Mapa Interactivo (React + Leaflet.js)
- **Objetivo**: Construir la interfaz de usuario interactiva para visualización del estado de las calles.
- **Entregables & Tecnologías** (`React`, `Leaflet.js`, `React-Leaflet`):
  - Mapa interactivo de Encarnación con capa de azulejos (tiles OpenStreetMap / CartoDB).
  - Renderizado de marcadores codificados por color (Verde/Amarillo/Rojo) y tamaño según gravedad.
  - Filtro interactivo por radio de búsqueda centrado en la ubicación del usuario o en un punto seleccionado.
  - Popup con imagen del keyframe y caja de detección dibujada, gravedad, confianza, coordenadas y fecha.
  - Acciones para reportar falso positivo o bache reparado/desactualizado; mostrar estado de envío y contadores, limitando votos repetidos según la política backend.
  - Reflejar que los baches invalidados o desactualizados dejan de aparecer en el mapa.
- **Estado**: payload API, endpoint y acciones de UI implementados en código; falta aplicar/verificar migración PostGIS y compilar/probar frontend en entorno con Node.

## Fase 9 — Integración End-to-End, Pruebas y Presentación
- **Objetivo**: Conectar todo el pipeline desde la entrada de video hasta la renderización en el mapa.
- **Entregables**:
  - Ejecutar y documentar el flujo (`Video + GPX` ➔ `YOLO + Tracking` ➔ `Georreferenciación` ➔ importación/PostGIS con deduplicación ➔ API ➔ React Map). La importación backend existe; no consta una orquestación automática ni validación integral con sesión real.
  - Validar con videos de calles reales de Encarnación y registrar resultados/limitaciones.
  - Completar registro real del montaje y GPS Logger en la guía de campo de `DOCUMENTACION.md`.
  - Revisar el manual de uso y preparar la demo después de ejecutar el flujo completo.
