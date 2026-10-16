#!/usr/bin/env python3
"""
Script para generar un archivo de texto con todo el código del proyecto
Uso: python3 generate_code_dump.py
"""

import os
from pathlib import Path

def generate_code_dump(project_root=".", output_file="project_code_dump.txt"):
    """
    Genera un archivo de texto con todo el código Python del proyecto.
    
    Args:
        project_root: Ruta raíz del proyecto
        output_file: Nombre del archivo de salida
    """
    
    py_files = []
    
    # Buscar todos los archivos .py
    for root, dirs, files in os.walk(project_root):
        # Ignorar directorios comunes que no queremos
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', '.env']]
        
        for file in sorted(files):
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                py_files.append(filepath)
    
    # Ordenar archivos por ruta
    py_files.sort()
    
    # Generar el archivo de salida
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("=" * 80 + "\n")
        out.write("COMPLETE PROJECT CODE DUMP\n")
        out.write("=" * 80 + "\n\n")
        out.write(f"Total Python files: {len(py_files)}\n\n")
        
        for filepath in py_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Escribir encabezado del archivo
                out.write("\n" + "=" * 80 + "\n")
                out.write(f"FILE: {filepath}\n")
                out.write("=" * 80 + "\n\n")
                
                # Escribir contenido
                out.write(content)
                out.write("\n\n")
                
                print(f"✓ {filepath}")
            
            except Exception as e:
                print(f"✗ {filepath} - Error: {e}")
    
    print(f"\n✅ Archivo generado: {output_file}")
    print(f"📊 Total de archivos: {len(py_files)}")
    
    # Mostrar tamaño del archivo
    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"📁 Tamaño: {size_mb:.2f} MB")

if __name__ == "__main__":
    # Ejecutar desde el directorio raíz del proyecto
    project_root = "."
    output_file = "project_code_dump.txt"
    
    print(f"Generando dump de código desde: {project_root}")
    print(f"Archivo de salida: {output_file}\n")
    
    generate_code_dump(project_root, output_file)
