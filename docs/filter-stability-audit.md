# Revisión de estabilidad de filtros

Fecha: 16 de octubre de 2026.

Se revisaron las diez operaciones activas de `core/filters.py`, la mezcla de
intensidad y la normalización de pantalla/exportación de `gui/app.py`.
Los resultados describen las entradas y parámetros probados; no garantizan
continuidad para cualquier imagen o combinación posible.

## Fallos reproducidos y corregidos

| Componente | Hallazgo | Cambio |
| --- | --- | --- |
| FNRGF | Mezcla de salida adimensional con intensidades originales; resultado dependiente de las unidades. | Conversión afín al rango de entrada antes de Strength, conservando los píxeles fuera del dominio. |
| FNRGF | Los anillos sin ninguna dispersión medible usaban un divisor artificial de una unidad. | Se conservan sin procesar en el modo estabilizado de la aplicación. Se mantiene el suelo del 5 % para los anillos con dispersión medible. |
| Pre-Asinh y Pre-Log | Épsilon y umbral absolutos anulaban o alteraban el filtro con intensidades pequeñas. | Normalización en coma flotante sin épsilon absoluto; tratamiento explícito del rango constante. |
| Pre-Log | El exponente cero se interpretaba como bypass, aunque significa K=1. | Se evalúa ln(1+x)/ln(2); desactivar la sección sigue siendo el bypass. |
| Puerta de ruido | El suelo absoluto de varianza alteraba el SNR con distintas unidades; el cuadrado podía desbordarse. El radio cambiaba a 100 px si era ≤5. | SNR en unidades normalizadas y doble precisión; caso explícito de desviación cero; uso del radio positivo indicado. |
| Suavizado y USM | Entradas enteras provocaban errores de tipos de OpenCV y devolvían silenciosamente el original. | Cálculo flotante y mezcla explícita; sin ocultar errores de ejecución. El suavizado admite ejes de un píxel. |
| MGN | Cuadrados float32 susceptibles a desbordamiento/subdesbordamiento en unidades extremas; recorte de enteros antes de convertirlos. | Conversión previa y reescalado interno únicamente en magnitudes extremas. Las pruebas de referencia habituales siguen pasando. |
| Exportación | MGN y puerta de ruido no escalaban sus núcleos con la resolución. | Sigmas multiplicadas por la relación original/previsualización. |
| Vista y exportación | Normalización con épsilon/umbral absoluto que alteraba imágenes de rango pequeño. | Normalización común sin constante absoluta, también para seleccionar el punto de simetría de GHS. |
| Entrada activa | NaN/Inf podían contaminar convoluciones o devolver silenciosamente el original. | Rechazo explícito en los filtros activos, al cargar y al ejecutar la tubería. |

El núcleo de referencia FNRGF conserva su opción sin estabilización para pruebas
numéricas. La aplicación activa el suelo de anchura y la conversión de unidades.
No se introduce recorte por percentiles por defecto.

## Comprobaciones

- 474 ejecuciones sintéticas: ceros, constantes, ruido positivo, valores con signo,
  diagonal de impulsos y corona artificial; extremos y valores cercanos de los
  controles principales de los diez filtros. Sin mutaciones de entrada,
  avisos numéricos ni valores no finitos después de las correcciones.
- 150 casos adicionales permanentes cubren controles secundarios, límites y
  valores vecinos: gamma/k/h/truncación, radios, ganancia, máscara, anillos,
  segmentos, coeficientes, STD/MAD y espaciado lineal/logarítmico.
- Comparación de las mismas intensidades con factores 1e-25, 1e-8, 65535 y 1e25;
  entradas uint16 frente a float32; bypass exacto y sin alias; NaN e infinitos;
  constantes negativas y ejes de un píxel. WOW también con denoising y bilateral.
- 103 ejecuciones sobre el TIFF facilitado, reducido a 512 y 1500 px y a su
  resolución original de 2308 × 2308. Los diez filtros producen resultados
  finitos sin avisos numéricos. La corrección posterior del exponente cero de
  Pre-Log se volvió a comprobar por separado con ese mismo TIFF.
- FNRGF, órdenes 20→21 y 21→22: cambio medio absoluto en la salida normalizada
  de aproximadamente 0,0038 % y 0,0035 % a 1500 px; 0,0025 % y 0,0016 % a
  resolución original, con Strength 32 %, 64 segmentos y los ajustes radiales
  de las capturas. Esta métrica se calcula antes de MGN y del estirado de pantalla.
- Exportación real del TIFF con FNRGF, MGN y puerta de ruido: archivos temporales
  leídos de vuelta; TIFF uint16 de 2308 × 2308 y JPEG de iguales dimensiones.
  La imagen original no se sobrescribió. Una prueba automatizada verifica además
  los argumentos de escala y el número de anillos enviados a los filtros.
- Tubería sintética con todas las familias activas, verificación de finalización,
  salida finita y preservación de entrada. Pruebas de referencia existentes de
  MGN, RHEF, FNRGF, WOW y ACHF conservadas.

## Diferencias que siguen siendo esperables

- WOW cambia de descomposición al cambiar el número entero de escalas; Auto puede
  seleccionar más escalas en una imagen de mayor resolución.
- Cambiar el número de segmentos, anillos, coeficientes o límites de aplicación
  modifica las muestras utilizadas. RHEF asigna rangos discretos; ACHF cambia
  vecinos al cruzar su umbral de intensidad o añadir puntos a su soporte circular.
  Estos cambios no equivalen a una singularidad de división.
- La previsualización y la exportación no son idénticas píxel a píxel: el
  remuestreo modifica ruido, estadísticas locales y rangos. Los tamaños físicos
  de suavizado se compensan donde corresponde; FNRGF conserva el recálculo de
  anillos solicitado y RHEF mantiene su ancho escalado en exportación.
- La vista sigue usando mínimos y máximos reales. Un valor extremo presente en
  los datos puede cambiar el contraste global; no se ha ocultado mediante un
  nuevo recorte automático.
- El TIFF y el JPEG no incluyen el mismo estirado de presentación que la vista:
  el TIFF es la salida normalizada a 16 bits y el JPEG aplica gamma 2,2. Es el
  comportamiento existente y no se cambió durante esta revisión.

Pruebas reproducibles: `python -m unittest discover -s tests -v`, dentro del
entorno con las dependencias del proyecto instaladas.
