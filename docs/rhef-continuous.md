# RHEF continuo global y ejecución compartida

En la sección RHEF, el selector ofrece:

- **Actual / compatible**: algoritmo de rangos exactos por anillo existente,
  conservado como predeterminado.
- **Continuo global**: estima 257 cuantiles de log-intensidad por anillo,
  interpola las distribuciones entre radios e invierte esa distribución en cada
  píxel. La imagen no se desenfoca. Sigue utilizando Strength, App Radius,
  Upsilon y Ring Width.

El modo continuo utiliza solo muestras positivas, finitas y seleccionadas.
Un anillo necesita al menos 12 muestras. No se interpolan estadísticas a través
de anillos vacíos ni se inventan datos en ellos. El núcleo devuelve NaN donde
no puede calcular un rango; al mezclar, esos píxeles conservan la entrada.
El interior de App Radius también se conserva. Las distribuciones constantes
se asignan a 0,5 y los empates usan el punto medio de su intervalo de cuantiles.
No es idéntico a rankdata: la distribución se aproxima mediante cuantiles.

La idea de interpolar estadísticas radiales se estudió en Agentic Eclipse
Library 1.3.2 (Pere Guerra Serra). El núcleo global se ha implementado aquí sin
incorporar el paquete AEL ni sus módulos. El estudio previo y las referencias
están en [ael-filter-review.md](ael-filter-review.md).

## Una sola ejecución

`core/pipeline.py` contiene `execute_pipeline`, usado tanto por FilterWorker
(en la previsualización Qt) como por la exportación. La secuencia es:

Pre-stretch → Noise Gate → suavizado → FNRGF → MGN → WOW → RHEF → USM → ACHF.

`collect_filter_parameters` toma una instantánea de la configuración de la GUI.
`prepare_parameters` adapta esa receta a la resolución de destino. La
exportación conserva una copia de los datos y parámetros antes de procesar
nuevos eventos Qt. No quedan dos cadenas separadas que haya que actualizar al
incorporar otra variante.

Las coordenadas se transforman por centro de píxel, con factores X/Y separados.
Los radios y núcleos circulares usan la media geométrica de esos factores para
compensar el pequeño cambio de aspecto causado por redondear dimensiones. Los
parámetros adimensionales, modos y grados se conservan. Sigma MGN, Noise Gate,
USM, suavizado, ACHF y ancho RHEF se escalan en píxeles; el número de anillos
FNRGF sigue aumentando en exportación según la resolución, como se pidió antes.
Los antiguos redondeos enteros de algunos núcleos de exportación ya no son
necesarios. No se promete identidad píxel a píxel con una imagen remuestreada.

Esta entrega comparte ejecución y configuración de resolución. No introduce aún
NRGF, RHEF local, una GUI de máscaras, color, ni un modelo general de capas.
El núcleo RHEF continuo ya admite una máscara `valid` para sus pruebas y usos
numéricos; los filtros antiguos conservan su contrato de entrada finita.

## Validación

- Cadena completa compatible: comparación exacta contra el ejecutor anterior
  del historial, en resolución de preview con todas las etapas activas.
- Receta común: mismo resultado al ejecutar por señales Qt o de forma síncrona.
- Geometría rectangular y escalado de controles; modo continuo transmitido desde
  la GUI a preview y exportación.
- Cuantiles frente a una referencia escalar independiente; empates, constantes,
  máscaras, datos no positivos/no finitos, huecos y anillos poco poblados.
- Misma imagen en unidades multiplicadas por 1e-25, 1e-8, 65535 y 1e25.
- Perfil radial pronunciado: comparación contra rangos discretos y contra el
  control aplanado, con un anillo artificial que la prueba debe detectar.
- Preservación del signo de una estructura tenue inyectada.
- Exportación real temporal TIFF uint16 y JPEG, con lectura posterior y
  verificación de dimensiones; RHEF continuo participa en esa prueba.
- TIFF del usuario comprobado a 1500 y 2308 px con el nuevo motor.

Para probar los cambios desde el código: `uv run main.py` y seleccionar
**RHEF → Continuo global**. No se cambia automáticamente el modo de una sesión
ya abierta.
