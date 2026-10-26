# Roadmap y Fases de Desarrollo - SAD Pothole Map (SPM)

> [!NOTE]
> **Aclaración Arquitectónica Principal**: El sistema procesa video grabado (modo offline / diferido). El concepto de "tiempo real" se refiere a la velocidad y eficiencia de procesamiento por fotograma del modelo (FPS sostenidos), lo cual elimina la necesidad de cómputo en vivo a bordo del vehículo y simplifica significativamente la arquitectura de despliegue.

## Stack Tecnológico Definido

| Capa | Tecnologías Seleccionadas |
| :--- | :--- |
| **Frontend** | React, Leaflet.js, React-Leaflet, Vanilla CSS / TailwindCSS |
| **Backend API** | Django, Django REST Framework (DRF), Python |
| **Base de Datos** | PostgreSQL + PostGIS (Soporte geoespacial nativo) |
| **IA & Visión por Computadora** | Python, Ultralytics YOLO (v8/v11), OpenCV, PyTorch, ByteTrack / BoT-SORT |
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
- **Entregables & Tecnologías** (`Ultralytics YOLOv8/v11`, `PyTorch`):
  - Entrenamiento supervisado del modelo YOLO.
  - Evaluación cuantitativa con métricas `mAP@50`, `mAP@50-95`, `Precision`, `Recall`.
  - Ajuste fine-tuning e hiperparámetros.
  - Matriz de confusión y análisis de falsos positivos/negativos.

## Fase 4 — Clasificación de Gravedad y Lógica de Negocio
- **Objetivo**: Determinar el nivel de severidad de cada bache detectado.
- **Entregables**:
  - Implementación de modelo multi-clase en YOLO (`leve`, `moderado`, `critico`) o algoritmo de área relativa (ratio área bache vs área del frame/calzada).
  - Clasificación tripartita visual: Verde (Leve), Amarillo (Moderado), Rojo (Crítico).
  - Documentación técnica justificativa sobre el procesamiento con cámara monocular (sin sensores 3D/LiDAR).

## Fase 5 — Pipeline de Video, Tracking Temporal y Georreferenciación
- **Objetivo**: Procesar videos completos, rastrear baches cuadro a cuadro y asociar coordenadas GPS.
- **Entregables & Tecnologías** (`OpenCV`, `ByteTrack / BoT-SORT`, `gpxpy`):
  - Inferencia batch sobre video completo.
  - Tracking multi-objeto con ByteTrack para resumir detecciones por ID dentro de una sesión.
  - Interpolación lineal del track GPX para asignar latitud/longitud al keyframe de mayor confianza, usando timestamps UTC de `frames.csv`.
  - Exportación local de baches únicos y evidencia a `processed_potholes.json` y `crops/` mediante `capture/process_video.py`.
- **Pendiente**: carga a Django, deduplicación espacial entre sesiones y calibración de desfase GPS.

## Fase 6 — Deduplicación Espacial
- **Objetivo**: Evitar registros duplicados de un mismo bache entre diferentes pasadas por la misma ruta.
- **Entregables & Tecnologías** (`DBSCAN / Scikit-Learn`, `PostGIS ST_ClusterDBSCAN`):
  - Clustering de coordenadas geográficas dentro de un umbral de proximidad (ej. 2 - 3 metros).
  - Consolidación del bache representativo (mejor nivel de confianza / foto más nítida).

## Fase 7 — Backend REST API & Base de Datos Espacial (Django + PostgreSQL)
- **Objetivo**: Desarrollar la infraestructura servidora para almacenamiento y consulta espacial de baches.
- **Entregables & Tecnologías** (`Django`, `Django REST Framework`, `PostgreSQL + PostGIS`):
  - Modelos de datos para Baches (geometría Point, gravedad, foto_url, confianza, timestamp).
  - Endpoints REST para consulta geoespacial: baches por radio/bounding box.
  - Script de ingesta / carga masiva desde el pipeline de video hacia la API.

## Fase 8 — Frontend Mapa Interactivo (React + Leaflet.js)
- **Objetivo**: Construir la interfaz de usuario interactiva para visualización del estado de las calles.
- **Entregables & Tecnologías** (`React`, `Leaflet.js`, `React-Leaflet`):
  - Mapa interactivo de Encarnación con capa de azulejos (tiles OpenStreetMap / CartoDB).
  - Renderizado de marcadores codificados por color (Verde/Amarillo/Rojo) y tamaño según gravedad.
  - Filtro interactivo por radio de búsqueda centrado en la ubicación del usuario o en un punto seleccionado.
  - Popups con imagen del bache, nivel de confianza, coordenadas y fecha.

## Fase 9 — Integración End-to-End, Pruebas y Presentación
- **Objetivo**: Conectar todo el pipeline desde la entrada de video hasta la renderización en el mapa.
- **Entregables**:
  - Script de ejecución orquestada end-to-end (`Video + GPX` ➔ `YOLO + Tracking` ➔ `Georreferenciación + Deduplicación` ➔ `Django API` ➔ `React Map`).
  - Validación general con videos de prueba de calles reales de Encarnación.
  - Documentación final del proyecto y manual de demostración.