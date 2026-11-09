# Informe científico (formato IEEE)

- `informe.tex`: el informe, con la plantilla IEEE de conferencia (`IEEEtran`, dos columnas).
- `figuras/`: figuras del informe (PDF vectorial y una foto JPG).
- `generar_figuras.py`: regenera las figuras con datos del repositorio y del checkpoint V4.

## Compilar

En Overleaf: **New Project → Upload Project**, subir `informe.tex` y la carpeta
`figuras/` (o un zip de esta carpeta) y compilar con pdfLaTeX. `IEEEtran` ya
viene incluido en Overleaf.

Para regenerar las figuras (desde la raíz del repositorio, con las
dependencias de `capture/` instaladas):

```
python informe_ieee/generar_figuras.py . informe_ieee/figuras [ruta/a/sesion_20261107_174903_f000214.jpg]
```

El script también genera PNG de control que no hace falta subir.

## Antes de entregar

1. **Ajustar a exactamente 3 páginas.** La primera compilación dio 4 páginas;
   el texto se redujo en consecuencia (cuerpo de ~1650 a ~1125 palabras, sin la
   foto de ejemplo ni la tabla de la prueba de campo).
   - Si sobra espacio: descomentar las figuras opcionales de la sección de
     resultados (foto de ejemplo y curvas de validación).
   - Si aún falta espacio: quitar la Fig. de mAP por tamaño y dejar sus valores
     en el texto.
2. Verificar en la nota de Más Encarnación la fecha de publicación citada
   (7/7/2026).
