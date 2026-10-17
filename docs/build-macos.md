# Aplicación de macOS

Desde la raíz del proyecto, con el entorno `.venv` creado:

```bash
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-build.txt
.venv/bin/python scripts/build_macos.py
```

Para generar también el DMG de instalación por arrastre:

```bash
.venv/bin/python scripts/build_macos.py --dmg
```

`dist/Corona Enhance Filters.dmg` contiene la aplicación y un acceso directo a
Aplicaciones. Abre el DMG y arrastra la aplicación sobre ese acceso para instalarla.

El resultado es `dist/Corona Enhance Filters.app`. Se puede abrir desde Finder y copiar
a Aplicaciones. Incluye Python, las dependencias y el icono seleccionado, por lo
que no necesita `uv` para ejecutarse.

El script genera un ICNS nuevo desde
`assets/icon-options/03-realce-coronal.png`, y lo incorpora al paquete para Finder
y el Dock. La aplicación usa el mismo PNG para la ventana y la barra de menús.
Los archivos intermedios y la configuración generada de PyInstaller quedan en
`build/macos`; tanto `build/` como `dist/` están excluidos de Git.

La arquitectura corresponde al Python usado para compilar: la compilación hecha
en este Mac es arm64 (Apple Silicon). Para Intel se necesita una compilación
con Python y dependencias x86_64. Esta compilación local no está notarizada por
Apple; para distribuirla públicamente conviene preparar firma Developer ID y
notarización por separado.

Ejecutar otra vez el script reemplaza los resultados anteriores de la compilación.
