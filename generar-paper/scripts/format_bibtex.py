#!/usr/bin/env python3
"""
Formateador y Limpiador de BibTeX
Formatea, limpia, ordena y deduplica archivos BibTeX.
"""

import sys
import re
import argparse
from typing import List, Dict
from collections import OrderedDict

class FormateadorBibTeX:
    """Formatea y limpia entradas BibTeX."""

    def __init__(self):
        # Orden estándar de campos para legibilidad
        self.orden_campos = [
            'author', 'editor', 'title', 'booktitle', 'journal',
            'year', 'month', 'volume', 'number', 'pages',
            'publisher', 'address', 'edition', 'series',
            'school', 'institution', 'organization',
            'howpublished', 'doi', 'url', 'isbn', 'issn',
            'note', 'abstract', 'keywords'
        ]

    def parsear_archivo_bibtex(self, ruta: str) -> List[Dict]:
        """
        Parsea un archivo BibTeX y extrae sus entradas.

        Args:
            ruta: Ruta al archivo BibTeX

        Returns:
            Lista de diccionarios de entrada
        """
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
        except Exception as e:
            print(f'Error al leer el archivo: {e}', file=sys.stderr)
            return []

        entradas = []

        # Encontrar entradas BibTeX
        patron = r'@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)\n\}'
        coincidencias = re.finditer(patron, contenido, re.DOTALL | re.IGNORECASE)

        for match in coincidencias:
            tipo_entrada = match.group(1).lower()
            clave = match.group(2).strip()
            texto_campos = match.group(3)

            # Parsear campos
            campos = OrderedDict()
            patron_campo = r'(\w+)\s*=\s*\{([^}]*)\}|(\w+)\s*=\s*"([^"]*)"'
            coincidencias_campo = re.finditer(patron_campo, texto_campos)

            for match_campo in coincidencias_campo:
                if match_campo.group(1):
                    nombre_campo = match_campo.group(1).lower()
                    valor_campo = match_campo.group(2)
                else:
                    nombre_campo = match_campo.group(3).lower()
                    valor_campo = match_campo.group(4)

                campos[nombre_campo] = valor_campo.strip()

            entradas.append({
                'tipo': tipo_entrada,
                'clave': clave,
                'campos': campos
            })

        return entradas

    def formatear_entrada(self, entrada: Dict) -> str:
        """
        Formatea una sola entrada BibTeX.

        Args:
            entrada: Diccionario de entrada

        Returns:
            Cadena BibTeX formateada
        """
        lineas = [f'@{entrada["tipo"]}{{{entrada["clave"]},']

        # Ordenar campos según el orden estándar
        campos_ordenados = OrderedDict()

        # Agregar campos en orden estándar
        for nombre_campo in self.orden_campos:
            if nombre_campo in entrada['campos']:
                campos_ordenados[nombre_campo] = entrada['campos'][nombre_campo]

        # Agregar campos restantes
        for nombre_campo, valor_campo in entrada['campos'].items():
            if nombre_campo not in campos_ordenados:
                campos_ordenados[nombre_campo] = valor_campo

        # Formatear cada campo
        max_longitud = max(len(c) for c in campos_ordenados.keys()) if campos_ordenados else 0

        for nombre_campo, valor_campo in campos_ordenados.items():
            # Rellenar nombre del campo para alineación
            campo_relleno = nombre_campo.ljust(max_longitud)
            lineas.append(f'  {campo_relleno} = {{{valor_campo}}},')

        # Quitar coma final del último campo
        if lineas[-1].endswith(','):
            lineas[-1] = lineas[-1][:-1]

        lineas.append('}')

        return '\n'.join(lineas)

    def corregir_problemas_comunes(self, entrada: Dict) -> Dict:
        """
        Corrige problemas comunes de formato en una entrada.

        Args:
            entrada: Diccionario de entrada

        Returns:
            Diccionario de entrada corregido
        """
        corregida = entrada.copy()
        campos = corregida['campos'].copy()

        # Corregir rangos de páginas (guion simple a guion doble)
        if 'pages' in campos:
            paginas = campos['pages']
            if re.search(r'\d-\d', paginas) and '--' not in paginas:
                paginas = re.sub(r'(\d)-(\d)', r'\1--\2', paginas)
                campos['pages'] = paginas

        # Quitar "pp." de páginas
        if 'pages' in campos:
            paginas = campos['pages']
            paginas = re.sub(r'^pp\.\s*', '', paginas, flags=re.IGNORECASE)
            campos['pages'] = paginas

        # Corregir DOI (quitar prefijo URL si está presente)
        if 'doi' in campos:
            doi = campos['doi']
            doi = doi.replace('https://doi.org/', '')
            doi = doi.replace('http://doi.org/', '')
            doi = doi.replace('doi:', '')
            campos['doi'] = doi

        # Corregir separadores de autores (punto y coma o ampersand a 'and')
        if 'author' in campos:
            autor = campos['author']
            autor = autor.replace(';', ' and')
            autor = autor.replace(' & ', ' and ')
            # Limpiar múltiples 'and'
            autor = re.sub(r'\s+and\s+and\s+', ' and ', autor)
            campos['author'] = autor

        corregida['campos'] = campos
        return corregida

    def deduplicar_entradas(self, entradas: List[Dict]) -> List[Dict]:
        """
        Elimina entradas duplicadas basándose en DOI o clave de cita.

        Args:
            entradas: Lista de diccionarios de entrada

        Returns:
            Lista de entradas únicas
        """
        dois_vistos = set()
        claves_vistas = set()
        entradas_unicas = []

        for entrada in entradas:
            doi = entrada['campos'].get('doi', '').strip()
            clave = entrada['clave']

            # Verificar DOI primero (más confiable)
            if doi:
                if doi in dois_vistos:
                    print(f'DOI duplicado encontrado: {doi} (omitiendo {clave})', file=sys.stderr)
                    continue
                dois_vistos.add(doi)

            # Verificar clave de cita
            if clave in claves_vistas:
                print(f'Clave de cita duplicada encontrada: {clave} (omitiendo)', file=sys.stderr)
                continue
            claves_vistas.add(clave)

            entradas_unicas.append(entrada)

        return entradas_unicas

    def ordenar_entradas(self, entradas: List[Dict], ordenar_por: str = 'key', descendente: bool = False) -> List[Dict]:
        """
        Ordena entradas por el campo especificado.

        Args:
            entradas: Lista de diccionarios de entrada
            ordenar_por: Campo por el cual ordenar ('key', 'year', 'author', 'title')
            descendente: Ordenar en orden descendente

        Returns:
            Lista de entradas ordenadas
        """
        def clave_orden(entrada: Dict) -> str:
            if ordenar_por == 'key':
                return entrada['clave'].lower()
            elif ordenar_por == 'year':
                year = entrada['campos'].get('year', '9999')
                return year
            elif ordenar_por == 'author':
                autor = entrada['campos'].get('author', 'ZZZ')
                # Obtener apellido del primer autor
                if ',' in autor:
                    return autor.split(',')[0].lower()
                else:
                    return autor.split()[0].lower() if autor else 'zzz'
            elif ordenar_por == 'title':
                return entrada['campos'].get('title', '').lower()
            else:
                return entrada['clave'].lower()

        return sorted(entradas, key=clave_orden, reverse=descendente)

    def formatear_archivo(self, ruta: str, salida: str = None,
                         deduplicar: bool = False, ordenar_por: str = None,
                         descendente: bool = False, corregir: bool = True) -> None:
        """
        Formatea un archivo BibTeX completo.

        Args:
            ruta: Archivo BibTeX de entrada
            salida: Archivo de salida (None para modificar en el lugar)
            deduplicar: Eliminar duplicados
            ordenar_por: Campo por el cual ordenar
            descendente: Ordenar en orden descendente
            corregir: Corregir problemas comunes de formato
        """
        print(f'Parseando {ruta}...', file=sys.stderr)
        entradas = self.parsear_archivo_bibtex(ruta)

        if not entradas:
            print('No se encontraron entradas', file=sys.stderr)
            return

        print(f'Encontradas {len(entradas)} entradas', file=sys.stderr)

        # Corregir problemas comunes
        if corregir:
            print('Corrigiendo problemas comunes...', file=sys.stderr)
            entradas = [self.corregir_problemas_comunes(e) for e in entradas]

        # Deduplicar
        if deduplicar:
            print('Eliminando duplicados...', file=sys.stderr)
            cantidad_original = len(entradas)
            entradas = self.deduplicar_entradas(entradas)
            eliminados = cantidad_original - len(entradas)
            if eliminados > 0:
                print(f'Eliminados {eliminados} duplicado(s)', file=sys.stderr)

        # Ordenar
        if ordenar_por:
            print(f'Ordenando por {ordenar_por}...', file=sys.stderr)
            entradas = self.ordenar_entradas(entradas, ordenar_por, descendente)

        # Formatear entradas
        print('Formateando entradas...', file=sys.stderr)
        entradas_formateadas = [self.formatear_entrada(e) for e in entradas]

        # Escribir salida
        contenido_salida = '\n\n'.join(entradas_formateadas) + '\n'

        archivo_salida = salida or ruta
        try:
            with open(archivo_salida, 'w', encoding='utf-8') as f:
                f.write(contenido_salida)
            print(f'Se escribieron {len(entradas)} entradas en {archivo_salida}', file=sys.stderr)
        except Exception as e:
            print(f'Error al escribir el archivo: {e}', file=sys.stderr)
            sys.exit(1)


def principal():
    """Interfaz de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Formatea, limpia, ordena y deduplica archivos BibTeX',
        epilog='Ejemplo: python format_bibtex.py referencias.bib --deduplicate --sort year'
    )

    parser.add_argument(
        'archivo',
        help='Archivo BibTeX a formatear'
    )

    parser.add_argument(
        '-o', '--output',
        help='Archivo de salida (por defecto: sobrescribe el archivo de entrada)'
    )

    parser.add_argument(
        '--deduplicate',
        action='store_true',
        help='Eliminar entradas duplicadas'
    )

    parser.add_argument(
        '--sort',
        choices=['key', 'year', 'author', 'title'],
        help='Ordenar entradas por campo'
    )

    parser.add_argument(
        '--descending',
        action='store_true',
        help='Ordenar en orden descendente'
    )

    parser.add_argument(
        '--no-fix',
        action='store_true',
        help='No corregir problemas comunes'
    )

    args = parser.parse_args()

    # Formatear archivo
    formateador = FormateadorBibTeX()
    formateador.formatear_archivo(
        args.archivo,
        salida=args.output,
        deduplicar=args.deduplicate,
        ordenar_por=args.sort,
        descendente=args.descending,
        corregir=not args.no_fix
    )


if __name__ == '__main__':
    principal()
