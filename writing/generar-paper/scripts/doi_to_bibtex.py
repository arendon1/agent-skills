#!/usr/bin/env python3
"""
Conversor de DOI a BibTeX
Convierte DOIs a formato BibTeX usando la API de CrossRef.
"""

import sys
import requests
import argparse
import time
import json
from typing import Optional, List

class ConversorDOI:
    """Convierte DOIs a entradas BibTeX usando la API de CrossRef."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ConversorDOI/2.0 (Herramienta de Gestión de Citas; mailto:support@example.com)'
        })

    def doi_a_bibtex(self, doi: str) -> Optional[str]:
        """
        Convierte un solo DOI a formato BibTeX.

        Args:
            doi: Digital Object Identifier

        Returns:
            Cadena BibTeX o None si la conversión falla
        """
        # Limpiar DOI (quitar prefijo URL si está presente)
        doi = doi.strip()
        if doi.startswith('https://doi.org/'):
            doi = doi.replace('https://doi.org/', '')
        elif doi.startswith('http://doi.org/'):
            doi = doi.replace('http://doi.org/', '')
        elif doi.startswith('doi:'):
            doi = doi.replace('doi:', '')

        # Solicitar BibTeX mediante negociación de contenido de CrossRef
        url = f'https://doi.org/{doi}'
        headers = {
            'Accept': 'application/x-bibtex',
            'User-Agent': 'ConversorDOI/2.0 (Herramienta de Gestión de Citas)'
        }

        try:
            response = self.session.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                bibtex = response.text.strip()
                # CrossRef a veces devuelve entradas con tipo @data, convertir a @misc
                if bibtex.startswith('@data{'):
                    bibtex = bibtex.replace('@data{', '@misc{', 1)
                return bibtex
            elif response.status_code == 404:
                print(f'Error: DOI no encontrado: {doi}', file=sys.stderr)
                return None
            else:
                print(f'Error: Falló la obtención de BibTeX para {doi} (estado {response.status_code})', file=sys.stderr)
                return None

        except requests.exceptions.Timeout:
            print(f'Error: Tiempo de espera agotado para el DOI: {doi}', file=sys.stderr)
            return None
        except requests.exceptions.RequestException as e:
            print(f'Error: Falló la solicitud para {doi}: {e}', file=sys.stderr)
            return None

    def convertir_multiples(self, dois: List[str], espera: float = 0.5) -> List[str]:
        """
        Convierte múltiples DOIs a BibTeX.

        Args:
            dois: Lista de DOIs
            espera: Espera entre solicitudes (segundos) para límite de tasa

        Returns:
            Lista de entradas BibTeX (excluye conversiones fallidas)
        """
        entradas_bibtex = []

        for i, doi in enumerate(dois):
            print(f'Convirtiendo DOI {i+1}/{len(dois)}: {doi}', file=sys.stderr)
            bibtex = self.doi_a_bibtex(doi)

            if bibtex:
                entradas_bibtex.append(bibtex)

            # Límite de tasa
            if i < len(dois) - 1:  # No esperar después de la última solicitud
                time.sleep(espera)

        return entradas_bibtex


def principal():
    """Interfaz de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Convierte DOIs a formato BibTeX usando la API de CrossRef',
        epilog='Ejemplo: python doi_to_bibtex.py 10.1038/s41586-021-03819-2'
    )

    parser.add_argument(
        'dois',
        nargs='*',
        help='DOI(s) a convertir (puede pasar varios)'
    )

    parser.add_argument(
        '-i', '--input',
        help='Archivo de entrada con DOIs (uno por línea)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Archivo de salida para BibTeX (por defecto: stdout)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Espera entre solicitudes en segundos (por defecto: 0.5)'
    )

    parser.add_argument(
        '--format',
        choices=['bibtex', 'json'],
        default='bibtex',
        help='Formato de salida (por defecto: bibtex)'
    )

    args = parser.parse_args()

    # Recolectar DOIs desde línea de comandos y/o archivo
    dois = []

    if args.dois:
        dois.extend(args.dois)

    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                dois_archivo = [line.strip() for line in f if line.strip()]
                dois.extend(dois_archivo)
        except FileNotFoundError:
            print(f'Error: Archivo de entrada no encontrado: {args.input}', file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f'Error al leer el archivo de entrada: {e}', file=sys.stderr)
            sys.exit(1)

    if not dois:
        parser.print_help()
        sys.exit(1)

    # Convertir DOIs
    conversor = ConversorDOI()

    if len(dois) == 1:
        bibtex = conversor.doi_a_bibtex(dois[0])
        if bibtex:
            entradas_bibtex = [bibtex]
        else:
            sys.exit(1)
    else:
        entradas_bibtex = conversor.convertir_multiples(dois, espera=args.delay)

    if not entradas_bibtex:
        print('Error: No hubo conversiones exitosas', file=sys.stderr)
        sys.exit(1)

    # Formatear salida
    if args.format == 'bibtex':
        salida = '\n\n'.join(entradas_bibtex) + '\n'
    else:  # json
        salida = json.dumps({
            'total': len(entradas_bibtex),
            'entradas': entradas_bibtex
        }, indent=2)

    # Escribir salida
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(salida)
            print(f'Se escribieron {len(entradas_bibtex)} entradas en {args.output}', file=sys.stderr)
        except Exception as e:
            print(f'Error al escribir el archivo de salida: {e}', file=sys.stderr)
            sys.exit(1)
    else:
        print(salida)

    # Resumen
    if len(dois) > 1:
        tasa_exito = len(entradas_bibtex) / len(dois) * 100
        print(f'\nConvertidos {len(entradas_bibtex)}/{len(dois)} DOIs ({tasa_exito:.1f}%)', file=sys.stderr)


if __name__ == '__main__':
    principal()
