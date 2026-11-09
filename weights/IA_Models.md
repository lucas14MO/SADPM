# Modelos de detección de baches

Resumen de versiones (V4 es el modelo actual):

| Versión | Archivo | Arquitectura | Clases | Uso actual |
| --- | --- | --- | --- | --- |
| V4 | `weights_v4_monoclass.pt` | YOLO26 Small | 1: `pothole` | Procesamiento offline (`process_video.py`) y detección en vivo (`detect.py`) |
| V3 | `weights.pt` | YOLO26 Nano | 3: `pothole_critical`, `pothole_light`, `pothole_moderate` | Histórico; incompatible con el pipeline actual |
| V2 | No conservado | No documentada | 1 | Histórico |

## V4 monoclass (modelo actual)

### Identificación

| Campo | Valor | Fuente |
| --- | --- | --- |
| Model URL / identificador | `lucas-benitez/pothole-vhmow-bygvr-9-yolo26s-t1` | Roboflow |
| Tipo | YOLO26 Object Detection (Small), modelo base `yolo26s.pt` | Roboflow + checkpoint |
| Iteración de entrenamiento en Roboflow | 9 (sufijo `-9`) | Roboflow |
| Versión del dataset | 2026-11-08 4:38 PM | Roboflow |
| Actualizado en Roboflow | 8/11/2026, 4:59 PM | Roboflow |
| Fecha interna del checkpoint | 2026-11-08 19:54 UTC (16:54 hora de Paraguay) | Checkpoint |
| Licencia | AGPL-3.0 | Roboflow + checkpoint (Ultralytics) |
| Latencia (Cloud API de Roboflow) | 7,5 ms | Roboflow |
| URL de checkpoint | No indicada (`-`) | Roboflow |
| Parámetros | 9 948 638 | Checkpoint |
| SHA-256 | `542e3eea4fb813247abafe4866a510305ea89ab2062963fef1afe086e174280b` | Calculado sobre el archivo |

La fecha interna del checkpoint coincide con la actualización de Roboflow
(minutos de diferencia). Por eso se considera que `weights_v4_monoclass.pt` es
el modelo de la iteración 9.

### Dataset y entrenamiento

| Campo | Valor | Fuente |
| --- | --- | --- |
| Imágenes | 386 (143 propias + 243 seleccionadas de un dataset público) | Reportado por el equipo |
| Origen de las imágenes públicas | *Fork* de un dataset público de Roboflow | Reportado por el equipo |
| Conjunto de test | 37 imágenes (70 baches etiquetados) | Roboflow (evaluación del modelo) |
| Split train/valid | No informado | — |
| Épocas configuradas | 300 (`patience` 90) | Checkpoint |
| Mejor época (por mAP@50-95 de validación) | 281 | Checkpoint |
| Tamaño de entrada / batch | 640 px / 31 | Checkpoint |
| Optimizador / `lr0` / semilla | `auto` / 0,01 / 0 | Checkpoint |
| Versión de Ultralytics del entrenamiento | 8.4.55 | Checkpoint |

Falta el nombre y la URL del dataset público original (para citarlo y
verificar su licencia) y el split train/valid.

### Métricas

Hay **dos fuentes de métricas, con valores distintos**. No mezclarlas sin
indicar de dónde sale cada una.

**a) Gráfico de Roboflow** (versión del dataset 2026-11-08). Roboflow no indica
en el gráfico sobre qué split se calcularon.

| Métrica | Todos | Objetos chicos | Objetos medianos | Objetos grandes |
| --- | ---: | ---: | ---: | ---: |
| mAP@50 | 60,8 % | 0,0 % | 43,2 % | 75,3 % |
| mAP@50-95 | 28,3 % | 0,0 % | 15,8 % | 38,3 % |
| mAP@75 | 27,3 % | 0,0 % | 8,3 % | 42,5 % |

Gráfico original: [`Source/v4_map_por_tamano.png`](Source/v4_map_por_tamano.png).
Los tamaños siguen la convención COCO (chico: < 32×32 px; mediano: hasta
96×96 px; grande: más de 96×96 px, en la resolución evaluada). El 0 % en
objetos chicos significa que el modelo no detecta correctamente baches chicos,
o que el split evaluado casi no los tiene. Es relevante porque en la cámara del
vehículo los baches lejanos se ven chicos.

**b) Métricas guardadas en el checkpoint** (validación de Ultralytics, mejor
época 281, umbral de IoU 0,5 para P/R):

| Precisión | Recall | F1 (calculado) | mAP@50 | mAP@50-95 |
| ---: | ---: | ---: | ---: | ---: |
| 88,35 % | 66,05 % | 75,6 % | 69,93 % | 36,72 % |

El F1 se calcula como 2·P·R/(P+R) con esos valores. Las métricas de validación
suelen ser más altas que las de test, porque el split de validación se usa para
elegir la mejor época.

**Pérdidas** (gráficos de Roboflow): [`BoxLoss.png`](Source/BoxLoss.png),
[`ClassLoss.png`](Source/ClassLoss.png) y
[`ObjectLoss.png`](Source/ObjectLoss.png). En la mejor época el
checkpoint registra `val/box_loss` 2,253, `val/cls_loss` 1,464 y `val/dfl_loss`
0,018. En el gráfico "Object Loss" de Roboflow corresponde a `dfl_loss`: YOLO26
no tiene pérdida de objectness.

**c) Matriz de confusión en test** (Roboflow, conjunto de test de 37 imágenes,
70 baches): [`Source/v4_matriz_confusion_test.png`](Source/v4_matriz_confusion_test.png).
Filas: Ground Truth; columnas: Prediction.

| Ground Truth \\ Prediction | `pothole` | No detectado (FN) |
| --- | ---: | ---: |
| `pothole` | 45 | 25 |
| Fondo (falso positivo) | 14 | — |

| Precisión | Recall | F1 |
| ---: | ---: | ---: |
| 76,3 % | 64,3 % | 69,8 % |

Calculadas con la matriz: P = 45/(45+14), R = 45/(45+25), F1 = 2·45/(2·45+14+25).
Son las métricas de V4 **más confiables para el informe**, porque el test no se
usa para entrenar ni para elegir la época. El umbral de confianza de la
evaluación no se indica en la captura (Roboflow usa uno por defecto).

Comparadas con las de validación (P 88,4 %, R 66,1 %), el recall se mantiene y
la precisión baja 12 puntos: en imágenes nuevas el modelo marca más falsos
positivos. Coincide con la prueba de campo, donde aparecieron grietas y marcas
detectadas como baches.

### Rendimiento local (medido en este repositorio)

| Campo | Valor |
| --- | --- |
| Hardware | Intel Core i7-12700F (CPU, sin GPU), 32 GB RAM |
| Software | PyTorch 2.15 (CPU), Ultralytics 8.4.208 |
| Entrada | Fotogramas 1920×810, `imgsz` 640, `conf` 0,3 |
| Latencia media | ~51 ms por fotograma (~19 fps), incluyendo pre y posprocesamiento |

La latencia de 7,5 ms de Roboflow es de su API en la nube con GPU y no se
compara directamente con esta.

### Prueba de campo (7/11/2026, Encarnación)

Sobre 403 fotogramas (1 fps) de 5 sesiones con GPX:

| Indicador | Valor |
| --- | ---: |
| Fotogramas con al menos una detección | 93 |
| Detecciones (`conf` ≥ 0,3) | 117 |
| Detecciones dentro del ROI y georreferenciadas | 115 |
| Baches consolidados en PostGIS (DBSCAN, 2,5 m) | 89 |
| Severidad asignada | 61 leves, 28 moderados, 0 críticos |

No hay etiquetas de verdad de campo para esos fotogramas, así que **no se puede
calcular precisión ni recall de campo**. La inspección visual muestra falsos
positivos (grietas y marcas chicas). Además, esos fotogramas pueden estar entre
las 143 imágenes propias usadas para entrenar, así que no sirven como test.

## V3 multiclase (histórico)

`weights/weights.pt` es el checkpoint multiclase anterior, conservado por
reproducibilidad. El pipeline actual lo rechaza porque tiene más de una clase.

| Campo | Valor | Fuente |
| --- | --- | --- |
| Model URL / identificador | `lucas-benitez/pothole-vhmow-bygvr-4-yolo26n-t1` | Roboflow |
| Tipo | YOLO26 Object Detection (Nano) | Roboflow + checkpoint |
| Iteración en Roboflow | 4 (la tercera se descartó) | Roboflow |
| Versión del dataset | 2026-10-26 2:46 PM | Roboflow |
| Actualizado en Roboflow | 26/10/2026, 3:06 PM | Roboflow |
| Fecha interna del checkpoint | 2026-10-26 18:04 UTC (15:04 hora de Paraguay) | Checkpoint |
| Licencia | AGPL-3.0 | Roboflow + checkpoint |
| Latencia (Cloud API) | 7,3 ms | Roboflow |
| Parámetros | 2 504 970 | Checkpoint |
| SHA-256 | `2c4a2b4c81e2f890565c4f3a8ae3c3c5e5fccf1ac9943a06b7756b799f8cade2` | Calculado sobre el archivo |

"V3" es el nombre de la versión en este proyecto y corresponde a la iteración
4 de Roboflow. La fecha interna del checkpoint coincide con la actualización en
Roboflow, así que el archivo corresponde a esa iteración.

Dataset (según las notas del proyecto): dataset comunitario público purgado a
mano (~700 imágenes revisadas; 338 seleccionadas, más aumentos), división
70/20/10 y etiquetas propias de tres niveles de severidad.

### Métricas de V3

| Fuente | mAP@50 | mAP@50-95 | Precisión | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Notas del proyecto (Roboflow) | 39,2 % | 16,9 % | 63,1 % | 46,2 % | 52,6 % (registrado) / 53,3 % (calculado con P y R) |
| Checkpoint (validación, mejor época) | 33,03 % | 18,69 % | 50,51 % | 36,48 % | 42,4 % (calculado) |

El F1 registrado (52,6 %) no coincide con el que sale de la precisión y el
recall registrados (53,3 %). Puede ser un promedio por clase; hasta confirmarlo,
usar el valor calculado e indicar cómo se obtuvo.

Pérdidas del último registro del historial de entrenamiento: `val/dfl_loss`
0,021 (el "Object Loss" de Roboflow), `val/cls_loss` 3,0211 y `val/box_loss`
2,0772. Son **pérdidas de validación**, no de entrenamiento.

### Matriz de confusión de V3

[`Source/matris_confusion.png`](Source/matris_confusion.png) (original) y
[`Source/matris_confusion_labeled.svg`](Source/matris_confusion_labeled.svg)
(con etiquetas). Filas: Ground Truth; columnas: Prediction.

| Ground Truth \\ Prediction | `pothole_critical` | `pothole_light` | `pothole_moderate` | `false_negative` |
| --- | ---: | ---: | ---: | ---: |
| `pothole_critical` | 14 | 1 | 0 | 6 |
| `pothole_light` | 0 | 7 | 0 | 10 |
| `pothole_moderate` | 1 | 1 | 8 | 16 |
| `false_positive` | 0 | 9 | 6 | 0 |

Lectura: de 64 baches reales, el modelo detectó 32 (50 %) y no vio los otros 32.
De los 32 detectados, 29 tuvieron la severidad correcta (90,6 %). Además dio 15
falsos positivos. Es decir, V3 fallaba sobre todo en **encontrar** baches más
que en clasificar su severidad. Esto motivó V4: un detector de una sola clase,
con la severidad calculada aparte por área.

## V2 (histórico)

| Fecha | Clases | mAP@50 | Precisión | Recall | F1 |
| --- | --- | ---: | ---: | ---: | ---: |
| 10/10/2026 | 1 | 82,7 % | 86,4 % | 75,5 % | 80,6 % |

Dataset, split y checkpoint no documentados. No es comparable con V3 y V4
porque se evaluó sobre otro dataset.

## Métricas que pide el informe (formato IEEE) y estado

| Métrica pedida | Estado para V4 |
| --- | --- |
| mAP | ✅ Roboflow (60,8 % / 28,3 %) y checkpoint (69,9 % / 36,7 %) |
| F1-score | ✅ Test: 69,8 % (matriz de Roboflow). Validación: 75,6 % |
| Precisión / Recall | ✅ Test: 76,3 % / 64,3 %. Validación: 88,4 % / 66,1 % |
| Matriz de confusión | ✅ V4 en test (2×2) y V3 (3 clases) |
| Tiempo de inferencia | ✅ ~51 ms/fotograma en CPU local; 7,5 ms en la nube de Roboflow |
| Accuracy | ⚠️ No es una métrica estándar en detección de objetos (no hay "verdaderos negativos" contables). Se puede reportar la exactitud de severidad de V3 (90,6 % de los detectados) o justificar que no aplica |
| RMSE | ⚠️ No aplica a la detección. Se puede usar para el **error de georreferenciación**: medir con GPS la posición real de 10–20 baches y comparar con la del sistema. Requiere trabajo de campo |

## Pendiente

- Nombre, URL y licencia del dataset público de Roboflow del que se hizo el
  *fork* (para citarlo en el informe).
- Split train/valid de V4 y umbral de confianza usado en la evaluación de test.
- Para una evaluación de campo, etiquetar fotogramas de un recorrido **no usado
  en entrenamiento**, separando por recorrido para evitar fotogramas casi
  idénticos entre train y test.
