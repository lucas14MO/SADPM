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

1. **Verificar que sean exactamente 3 páginas.** Con el texto reducido (~1125
   palabras de cuerpo) el informe compiló en 3 páginas con la tercera casi
   vacía; por eso se reincorporaron la foto de detección y las curvas de
   validación. Si con ellas pasa a 4 páginas, quitar primero las curvas
   (`fig:curvas` y su párrafo) y después la foto (`fig:ejemplo`).
2. Verificar en la nota de Más Encarnación la fecha de publicación citada
   (7/7/2026).
