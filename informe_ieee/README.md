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
python informe_ieee/generar_figuras.py . informe_ieee/figuras
```

El script también genera PNG de control que no hace falta subir.

## Antes de entregar

1. Completar autores, carrera, institución y correos (marcados con `[...]`).
2. Resolver los `TODO` del `.tex`:
   - Un dato local con cita sobre el estado de las calles (MOPC, Municipalidad
     de Encarnación o prensa).
   - Confirmar cómo se extrajeron los fotogramas del dataset propio.
3. **Ajustar a exactamente 3 páginas.** El texto está calculado para unas 3
   páginas, pero no se pudo compilar acá. Si sobra espacio: ampliar la
   discusión. Si falta espacio, quitar en este orden:
   - la figura de curvas de validación (`fig:curvas`) y su párrafo,
   - la foto de ejemplo (`fig:ejemplo`),
   - la subsección "Métricas no reportadas" (resumirla en una frase).
4. Si se consigue la matriz de confusión de V4 desde Roboflow, agregarla en
   lugar de (o además de) la de V3 (Tabla III).
