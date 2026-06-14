#!/usr/bin/env python3
"""
Compilador Typst
Compila documentos Typst a PDF con validación de salida.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def verificar_typst() -> bool:
    """Verifica que Typst esté instalado en el entorno."""
    try:
        resultado = subprocess.run(
            ['typst', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if resultado.returncode == 0:
            version = resultado.stdout.strip()
            print(f'Typst detectado: {version}', file=sys.stderr)
            return True
        else:
            print('Error: Typst no está instalado o no funciona correctamente.', file=sys.stderr)
            return False
    except FileNotFoundError:
        print('Error: Typst no está instalado. Instálelo desde https://typst.app', file=sys.stderr)
        return False
    except Exception as e:
        print(f'Error al verificar Typst: {e}', file=sys.stderr)
        return False


def compilar(archivo_typ: str, salida: str = None, directorio_trabajo: str = None) -> bool:
    """
    Compila un archivo Typst a PDF y valida la salida.

    Args:
        archivo_typ: Ruta al archivo .typ de entrada
        salida: Ruta al archivo .pdf de salida (opcional)
        directorio_trabajo: Directorio de trabajo para la compilación

    Returns:
        True si la compilación fue exitosa
    """
    ruta_typ = Path(archivo_typ)

    if not ruta_typ.exists():
        print(f'Error: Archivo no encontrado: {archivo_typ}', file=sys.stderr)
        return False

    if ruta_typ.suffix != '.typ':
        print(f'Error: El archivo debe tener extensión .typ: {archivo_typ}', file=sys.stderr)
        return False

    # Determinar ruta de salida
    if salida:
        ruta_salida = Path(salida)
    else:
        ruta_salida = ruta_typ.with_suffix('.pdf')

    # Construir comando
    cmd = ['typst', 'compile', str(ruta_typ), str(ruta_salida)]

    if directorio_trabajo:
        cmd.extend(['--root', directorio_trabajo])

    print(f'Compilando: {" ".join(cmd)}', file=sys.stderr)

    try:
        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=directorio_trabajo or ruta_typ.parent
        )

        if resultado.returncode != 0:
            print(f'Error de compilación Typst:', file=sys.stderr)
            print(resultado.stderr, file=sys.stderr)

            # Buscar errores comunes
            stderr = resultado.stderr
            if 'unknown variable' in stderr or 'unknown function' in stderr:
                print('\n  Posible causa: variable o función no definida.', file=sys.stderr)
            if 'file not found' in stderr:
                print('\n  Posible causa: archivo de referencia no encontrado (¿.bib existe?).', file=sys.stderr)
            if 'syntax error' in stderr:
                print('\n  Posible causa: error de sintaxis en el código Typst.', file=sys.stderr)

            return False

        # Validar PDF generado
        if not ruta_salida.exists():
            print(f'Error: El PDF no se generó: {ruta_salida}', file=sys.stderr)
            return False

        tamano = ruta_salida.stat().st_size
        if tamano == 0:
            print(f'Error: El PDF generado está vacío (0 bytes): {ruta_salida}', file=sys.stderr)
            return False

        print(f'Compilación exitosa: {ruta_salida} ({tamano:,} bytes)', file=sys.stderr)

        # Advertencias de Typst (van a stderr incluso en éxito)
        if resultado.stderr:
            print(f'\nAdvertencias de Typst:', file=sys.stderr)
            for linea in resultado.stderr.strip().split('\n'):
                if 'warning' in linea.lower():
                    print(f'  {linea}', file=sys.stderr)

        return True

    except subprocess.TimeoutExpired:
        print('Error: La compilación excedió el tiempo límite (120s).', file=sys.stderr)
        return False
    except Exception as e:
        print(f'Error inesperado durante la compilación: {e}', file=sys.stderr)
        return False


def principal():
    """Interfaz de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Compila documentos Typst a PDF con validación de salida',
        epilog='Ejemplo: python compile.py paper.typ --output paper.pdf'
    )

    parser.add_argument(
        'archivo',
        help='Archivo Typst (.typ) a compilar'
    )

    parser.add_argument(
        '-o', '--output',
        help='Archivo PDF de salida (por defecto: mismo nombre que .typ)'
    )

    parser.add_argument(
        '--root',
        help='Directorio raíz para la compilación (resuelve rutas relativas)'
    )

    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Solo verificar que Typst esté instalado, sin compilar'
    )

    args = parser.parse_args()

    if args.check_only:
        if verificar_typst():
            print('Typst está instalado y funcionando.')
            sys.exit(0)
        else:
            sys.exit(1)

    # Verificar Typst
    if not verificar_typst():
        sys.exit(1)

    # Compilar
    exito = compilar(args.archivo, salida=args.output, directorio_trabajo=args.root)

    if exito:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    principal()
