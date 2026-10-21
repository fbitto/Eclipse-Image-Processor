# Revisión del apilado y propuesta de exportación por capas

17 de octubre de 2026. Análisis y propuesta; no se modifica el motor ni los originales.

## Dictamen

Sí recomiendo exportar una imagen final acompañada por capas independientes,
numeradas y con una receta de Photoshop. Debe ser una opción explícita de
exportación. Antes resolvería la diferencia entre presentación y exportación,
incorporaría máscaras y separaría cálculo del filtro, representación y mezcla.
Guardar las etapas intermedias de la cadena actual no produciría filtros independientes.

La carpeta estudiada es
`/Volumes/Astro/Imágenes/Eclipse_NEF/AEL_apilado_calibrado_20261017_01/Pipeline_filtros_PSB_01`.
Es un buen ejemplo de trazabilidad y un banco de comparación útil; su acabado
actual no debe convertirse en nuestro preset universal.

## Material y alcance

Se revisaron LEEME, parámetros Markdown/CSV/JSON, recetas de cálculo y presentación,
scripts de preparación y composición, banda lunar medida, informe de verificación,
vista final y las dos comparativas de 16 filtros. Se leyeron TIFF de base y final,
las cabeceras de las 16 capas flotantes y los arrays necesarios para recomponer
las tres capas activas. Se inspeccionaron imágenes de lienzo completo, comparativa
de detalle y un recorte de base/final a resolución nativa.

Se contrastó `core/pipeline.py`, `core/filters.py`, carga, render y exportación de
`gui/app.py`, y la revisión anterior `docs/ael-filter-review.md`. El código actual
ya comparte ejecución entre preview/export y ofrece RHEF continuo: esas partes de
la propuesta anterior ya están implementadas. La presentación sigue separada.

No se volvieron a apilar RAW ni a calcular los 16 filtros. No se ejecutaron los
otros dos programas ni se hizo una comprobación nativa en Photoshop. El informe
existente declara verificación completa del PSB; aquí se comprobó su cabecera y
una recomposición independiente del TIFF, no otra verificación integral del PSB.

## Lo que muestran los archivos y las imágenes

### Resultado y variantes

- Base y final: 5600 × 3728, RGB uint16, sin ICC incrustado. Máximos observados
  55729 y 54570 respectivamente; el máximo global no llega a 65535. Eso no demuestra
  conservación de todos los detalles o ausencia de recorte en etapas anteriores.
- Cabecera PSB: versión 2, RGB, 16 bits, 5600 × 3728. El archivo ocupa 2.09 GB;
  el informe registra 19 capas, de las que 16 son filtros.
- La carpeta `Capas_TIFF_float32` contiene 15 filtros float32 y MGN **float64**.
  Su nombre no garantiza el tipo real. Son representaciones de filtros entre
  cero y uno, con NaN fuera de dominio, no radiancia lineal de 32 bits.
- La mezcla activa usa NRGF Multiplicar 35%, RHEF Upsilon Multiplicar 10% y MGN
  Superponer 22%. Las otras 13 variantes están ocultas, preparadas al 30%.
- NRGF y RHEF globales ofrecen un resultado más contenido en las comparativas.
  Los sectores de RHEF acentúan variaciones locales; no los sumaría todos.
  Los ACHF isotrópicos producen lóbulos y bandas muy fuertes. El angular suavizado
  muestra textura radial dominante. Esto requiere controles; más contraste no
  equivale a estructura recuperada.
- MGN y WOW hacen visible mucho grano. La comparación al 30% no es una comparación
  a igual ganancia, ruido o contraste: las capas tienen normalizaciones distintas.
  Sirve para seleccionar candidatos, no para ordenar científicamente los métodos.
- El tono amarillo/verdoso está presente también en la base. Los documentos
  declaran RGB de cámara sin calibración: no atribuirlo exclusivamente al filtro
  ni corregirlo automáticamente suponiendo un blanco físico conocido.

### El borde claro tiene una explicación de composición comprobable

La envolvente lunar llega a 278.254 px frente a un radio de referencia de
274.051 px; con guarda de 8 px se decidió un margen de filtro de 13 px.
Es una decisión de este apilado, no una constante para otras imágenes.

En un recorte de 800 × 800, los alfa de las tres capas activas son cero entre
0 y 12 px exteriores al radio de referencia; su media entre 12 y 16 px es
0.7506 y valen uno entre 16 y 40 px. La base conserva su alfa original.
Al recomponer los arrays con modos y opacidades cuantizadas, el TIFF se reproduce
con error máximo de **1 código uint16**, y error medio de **0.000545 códigos**.

En Multiplicar, la mezcla es `C = B × (1 − a + a × F)`.
Una capa próxima a gris 0.5 al 35% deja aproximadamente 82.5% del brillo de base;
otra al 10% deja 95%. Juntas darían aproximadamente 78.4%, antes de MGN.
Donde el alfa es cero no existe ese oscurecimiento. Por tanto, esta receta puede
acentuar una franja clara por la transición entre base intacta y corona oscurecida.
El recorte nativo confirma un borde mucho más evidente en el final.

Esto identifica una contribución plausible y medible, no demuestra que sea la
única causa. El brillo del limbo original, la mezcla de exposiciones y la respuesta
unilateral de los kernels también deben comprobarse. Prueba siguiente: comparar
base, cada capa activa por separado y combinación, con perfiles radiales por
sectores y una corona sintética sin estructura. No rellenar la banda excluida ni
agrandar el disco para hacer desaparecer el borde.

## Qué incorporar de los repositorios

### Agentic Eclipse Library

Se revisó la distribución local 1.3.2 y el checkout
`5629b37071ec87a32f3cf37b5ce6dfcc8b02ada1`, además del repositorio público.
Adoptaría su separación de validez, cobertura, alfa y exclusión de entrada;
geometría explícita; capas calculadas desde un origen común; recibos reproducibles;
y verificación de exportación. NRGF continuo es el candidato radial que falta.
RHEF continuo ya existe aquí y merece comparación directa, no una sustitución ciega.

Mantendría nuestro WOW basado en watroo. El bilateral de AEL es otra implementación
y tiene controles fallidos documentados. Tampoco llamaría equivalentes al ACHF
circular adaptativo local y a los ACHF angular/isotrópicos de AEL.
Las capas portátiles no reproducen exactamente las capas históricas publicadas.
Fuente: [AEL](https://github.com/PeterWar/Agentic-Eclipse-Library),
[banco de filtros](https://github.com/PeterWar/Agentic-Eclipse-Library/blob/5629b37071ec87a32f3cf37b5ce6dfcc8b02ada1/ael/filterbank.py).

### EclipseForgeHDR

Código revisado en `b48bf59f0c2c8cd9ca92c6ae4405f1fd1e7e8395`, especialmente
`detail.py`, `render.py`, `importhdr.py` y LICENSE.
Interesan la inspección individual de capas, la convolución normalizada con
soporte y el ajuste local de pendiente radial junto al limbo. Este último aborda
el sesgo que una media unilateral introduce sobre un gradiente, incluso si se
normalizan sus pesos. También distingue sigma angular de tamaño físico de arco:
un kernel constante en grados crece en píxeles con el radio.

Probaría un realce tangencial moderado y detalle multiescala con máscara, como
opciones adicionales. Las capas de corona interior/protuberancias procedentes
de exposiciones cortas necesitan esos originales: no se recuperan desde un TIFF
ya combinado. El render contiene muchas decisiones específicas de su imagen;
no portaría el conjunto de constantes.

Su licencia permite ejecución en imágenes propias, pero no incorporar o redistribuir
su código en otro producto sin permiso. Lo usaría para comparación e ideas,
implementando desde métodos publicados o fuentes compatibles.
Fuentes: [repositorio](https://github.com/naugustin77/EclipseForgeHDR),
[código de detalle](https://github.com/naugustin77/EclipseForgeHDR/blob/b48bf59f0c2c8cd9ca92c6ae4405f1fd1e7e8395/src/eclipseforgehdr/detail.py),
[licencia](https://github.com/naugustin77/EclipseForgeHDR/blob/b48bf59f0c2c8cd9ca92c6ae4405f1fd1e7e8395/LICENSE).

### eclipsetools

Código revisado en `14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391`: convolución,
kernels, comandos de filtrado, preprocesamiento, correlación y ajuste fotométrico.
Es MIT. Su kernel separa sigma radial y tangencial y trata la discontinuidad
angular 0/2π. Es una referencia útil para una USM orientada según la geometría solar.

No trasladaría literalmente su comando de filtrado: convierte a Lab, reconstruye
una franja por ajuste de plano antes del desenfoque, recorta la salida y exporta
como sRGB. Ese contrato difiere de nuestro máster lineal y de conservar datos
ausentes. Su primitiva de convolución parcial es más aprovechable que ese flujo
completo; habría que evaluar rendimiento, soporte y sesgo de limbo.
Los ajustes fotométricos y alineación quedan para una futura etapa de apilado,
fuera del objetivo inmediato del editor de filtros.
Fuente: [convolución](https://github.com/naavis/eclipsetools/blob/14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391/src/eclipsetools/filtering/convolution.py),
[comandos](https://github.com/naavis/eclipsetools/blob/14ae3f7d823d0ac66688a32bf27d0c4b9b8a0391/src/eclipsetools/commands/filter.py).

### Referencia adicional

Usaría [sunkit-image](https://github.com/sunpy/sunkit-image) como referencia de
algoritmos publicados y [WOW oficial](https://docs.sunpy.org/projects/sunkit-image/en/stable/generated/gallery/watroo_wow.html)
para controles por escala y mapas de ruido. Ya utilizamos watroo; añadir otro
motor WOW no es prioritario. Los ejemplos solares espaciales no proporcionan
automáticamente un modelo de ruido válido para nuestro HDR terrestre remuestreado.

## Diferencias de nuestra aplicación que condicionan el diseño

1. `execute_pipeline` encadena preestirado, reducción de ruido, FNRGF, MGN, WOW,
   RHEF, USM y ACHF. Cada filtro modifica la entrada del siguiente. Exportar esos
   estados permite depurar la cadena, pero no mezclarlos como ramas independientes.
2. Los métodos `run_*` suelen incluir Strength y reescalado a unidades de entrada.
   No son automáticamente capas neutras para Superponer. Aplicar después una
   opacidad equivalente duplicaría la atenuación.
3. La carga convierte RGB a gris y descarta el cuarto canal; no conserva ICC ni
   máscaras del apilado. `finite_image` exige arrays completamente finitos y 2D.
   El TIFF flotante con NaN de esta carpeta no es una entrada compatible directa.
   Habrá que mantener máscara aparte y hacer los operadores conscientes de ella,
   sin sustituir NaN por ceros y tratar esos ceros como observaciones.
4. `render_matrix_to_screen` aplica normalización, estirado y mezcla original/procesado.
   `export_image_action` exporta el resultado normalizado del motor y un JPEG con
   gamma 2.2. No reutiliza esos controles de presentación. Compartir motor ha
   resuelto parte del problema, pero aún no garantiza «guardar lo que veo».
5. Las escalas espaciales ya se compensan entre preview y export. Para nuevas
   ramas deben mantenerse unidades explícitas: píxeles nativos, grados o R solares.

## Exportación propuesta

Dos modos compatibles: conservar la cadena actual y añadir una composición por
capas independientes. La salida del segundo sería la que Photoshop reconstruye.
No prometer que una mezcla de ramas reproduzca una cadena no lineal existente.

Cada rama parte del mismo máster y una preparación común declarada. Guardar si
hubo preestirado o reducción de ruido: una rama derivada de una preparación
estirada no debe etiquetarse como filtro del máster lineal sin más información.
Separar salida numérica, mapeo de capa y opacidad. El render final debe usar la
misma receta en la aplicación y en la exportación.

Ejemplo de paquete, numerado **desde abajo hacia arriba**:

```text
00_FINAL_16bit.tif                 # referencia visible; fuera de la pila editable
00_FINAL_preview.jpg
capas/
  01_BASE_Normal_100.tif
  02_NRGF_Multiply_035.tif
  03_RHEF_Upsilon_Multiply_010.tif
  04_MGN_Overlay_022.tif
  05_WOW_Overlay_000_OCULTA.tif
  06_Tangencial_Overlay_000_OCULTA.tif
  07_DetalleMultiescala_Overlay_000_OCULTA.tif
  mascaras/
receta.json
Layers.md
comparativa.jpg
```

Los nombres 02–04 reproducen **la receta estudiada**, con el borde pendiente de
resolver; no son parámetros validados para nuestras implementaciones. FNRGF
sería una alternativa al grupo radial y ACHF actual otra capa opcional. El banco
completo se exportaría únicamente al escoger «todas las variantes».

| Contenido de la capa | Modo inicial | Opacidad propuesta | Condición |
|---|---|---|---|
| Base de presentación | Normal | 100% | Color y estirado declarados |
| NRGF o FNRGF de estructura | Multiplicar si se prepara como modulación | 15–35% para explorar | Preferir una alternativa radial; revisar borde |
| RHEF Upsilon | Multiplicar | 5–10% para explorar | No duplicar contraste radial sin necesidad |
| MGN preparado para contraste | Superponer | 10–22% para explorar | Comparar grano y perfiles |
| WOW preparado para contraste | Superponer | 0% al exportar inicialmente | Activar y ajustar tras control de ruido |
| Residuo tangencial/multiescala | Superponer, gris 0.5 neutro | 0% inicialmente | Validar signo, ganancia, soporte y halos |
| Imagen ya procesada por `run_*` | Normal | Según mezcla explícita | No asumir neutralidad para Superponer |

Los intervalos son puntos de exploración visual, no resultados de optimización.
Las variantes ocultas son alternativas; activar todas acumularía detalle y ruido.
Una capa no debe incorporar ya la opacidad que se aplicará en Photoshop.

Especificaciones del paquete:

- TIFF uint16 para edición habitual; canales/máscaras compatibles, mismo lienzo,
  origen y orientación. Conservar float firmado, NaN y validez aparte cuando haya
  salidas numéricas; documentar sus unidades reales.
- Alfa sin premultiplicar cuando así lo requiera el importador, identificado
  explícitamente. Evitar aplicar dos veces el alfa de base en el borde.
- `receta.json`: orden, modo, visibilidad, opacidad nominal y efectiva, parámetros,
  preparación de entrada, escalas, geometría, máscaras, mapeo tonal, versión,
  hashes y espacio de mezcla. El nombre es una ayuda; el JSON es la receta completa.
- El ICC debe corresponder a una transformación real. Asignar sRGB a RGB de cámara
  no calibra el color. Para RGB final será necesario conservarlo desde la carga.
  Puede ofrecerse primero una edición monocroma, claramente identificada.
- TIFF sueltos necesitan instrucciones o un importador que configure modos,
  opacidades y máscaras: un nombre de archivo no configura Photoshop.
- PSB opcional después de estabilizar TIFF y compositor. Dimensionarlo por tamaño
  previsto, no solo por dimensiones. Este ejemplo ya ronda los 2 GB.
- Verificar lectura de TIFF, cuantización, alfa y recomposición; comprobar también
  Photoshop nativo, su perfil y ajustes de mezcla antes de prometer coincidencia.
  La imagen incrustada correcta en un PSB no basta para acreditar su render nativo.

## Prioridades y criterios de aceptación

**P0:** unificar presentación/exportación; conservar validez, alfa y metadatos;
aislar la causa del borde con cada capa por separado. Mantener un control sin filtros.

**P1:** ramas independientes, compositor y exportación TIFF + receta numerada.
Reutilizar RHEF continuo; añadir NRGF continuo. Una reconstrucción desde los TIFF
debe coincidir con el final dentro de una tolerancia uint16 documentada.

**P2:** convolución normalizada con corrección del sesgo de pendiente, tangencial
y multiescala; ruido por escala y diagnóstico de señal tenue. Controles sintéticos:
perfil radial puro, limbo descentrado, huecos de cobertura, sectores ausentes,
ruido correlacionado y filamentos positivos/negativos inyectados. No aceptar
anillos nuevos, inversiones de signo o costuras bajo una simple mejora estética.

**P3:** PSB y verificación nativa; conservación RGB/ICC completa y controles de
color. La exportación por capas aporta valor antes que sumar más variantes ACHF.

No se han ejecutado pruebas de regresión del programa en esta revisión porque
no hay cambios de implementación. Las comprobaciones descritas son de archivos,
lectura de código, inspección visual y recomposición del recorte indicado.
