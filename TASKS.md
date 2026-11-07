# Tareas pendientes

> Las pruebas con datos reales quedan pendientes hasta disponer de una sesión
> de video y su GPX. No intentar cerrar la validación end-to-end ni registrar
> métricas de campo sin esos datos.

## 7. Modelo: origen, dataset y métricas — Baja

- [x] Registrar la procedencia reportada de V3, arquitectura, dataset descrito y métricas disponibles en [weights/IA_Models.md](weights/IA_Models.md).
- [x] Registrar URL/identificador, iteración de entrenamiento, versión de dataset, tipo y latencia Cloud API de Roboflow en [IA_Models.md](weights/IA_Models.md).
- [x] Registrar la licencia reportada del modelo (AGPL-3.0).
- [ ] Confirmar si la licencia cubre también dataset/pesos, conseguir el checkpoint de Roboflow o verificar `weights/weights.pt` contra él, y guardar el checksum.
- [x] Añadir el mAP@50-95 (16,9%) y documentar la matriz de confusión con sus etiquetas y conteos en [IA_Models.md](weights/IA_Models.md).
- [ ] Conservar los reportes fuente de evaluación y aclarar si precisión, recall y F1 son globales, por clase o promedio, incluyendo el umbral usado; pendiente recuperar los artefactos de evaluación.
- [ ] Cuando haya videos propios, etiquetar fotogramas en Roboflow o CVAT y, si hay tiempo, reentrenar. Separar train/valid/test por recorrido para evitar fuga de fotogramas similares.

## 9. Documentación y presentación — Baja

- [x] Corregir estados de deduplicación e importación: DBSCAN espacial está implementado en el backend y `import_processed_potholes` importa sesiones procesadas y reconstruye consolidados.
- [x] Añadir protocolo reproducible de sincronización GPS y guía de montaje/calibración de cámara a [DOCUMENTACION.md](DOCUMENTACION.md). Las medidas reales del montaje y los ajustes del logger deben anotarse en campo; no están en el repositorio.
- [ ] **Conectar el mapa a la API real — Media.** En `frontend/.env.local`, configurar `VITE_USE_MOCK_DATA=false` y `VITE_API_BASE_URL` con la URL base del backend (por ejemplo `http://127.0.0.1:8000/api`). Luego verificar marcadores por color, filtro de severidad y panel con foto del bache.
- [ ] **Prueba completa con datos reales — pendiente de video/GPX.** Ejecutar video → `process_video.py` → importar sesión en PostGIS → comprobar resultados en el mapa. Registrar errores y resultado; dejar los testeos pendientes hasta contar con una sesión procesable.
- [ ] Completar la ficha de campo con dispositivo/app, configuración real del GPS Logger, precisión/frecuencia reportada y medidas reales del montaje cámara–antena (requiere levantamiento en campo).
- [ ] Preparar y revisar el manual de uso durante una ejecución completa siguiendo [DOCUMENTACION.md](DOCUMENTACION.md), incluida la importación descrita en `backend/README.md` (validación práctica pendiente de datos reales).
