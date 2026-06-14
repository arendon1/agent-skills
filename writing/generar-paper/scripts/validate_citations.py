#!/usr/bin/env python3
"""
Validador de Citas
Valida archivos BibTeX para precisión, completitud y conformidad de formato.
Incluye verificación por contenido (Tier C) con fallback a resolución (Tier B).
"""

import sys
import re
import requests
import argparse
import json
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from difflib import SequenceMatcher

class ValidadorCitas:
    """Valida entradas BibTeX en busca de errores e inconsistencias."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ValidadorCitas/2.0 (Herramienta de Gestión de Citas)'
        })

        # Campos requeridos por tipo de entrada
        self.campos_requeridos = {
            'article': ['author', 'title', 'journal', 'year'],
            'book': ['title', 'publisher', 'year'],  # author O editor
            'inproceedings': ['author', 'title', 'booktitle', 'year'],
            'incollection': ['author', 'title', 'booktitle', 'publisher', 'year'],
            'phdthesis': ['author', 'title', 'school', 'year'],
            'mastersthesis': ['author', 'title', 'school', 'year'],
            'techreport': ['author', 'title', 'institution', 'year'],
            'misc': ['title', 'year']
        }

        # Campos recomendados
        self.campos_recomendados = {
            'article': ['volume', 'pages', 'doi'],
            'book': ['isbn'],
            'inproceedings': ['pages'],
        }

        # Umbral de similitud para coincidencia difusa de títulos (Tier C)
        self.umbral_titulo = 0.85

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
            campos = {}
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
                'campos': campos,
                'crudo': match.group(0)
            })

        return entradas

    def validar_entrada(self, entrada: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Valida una sola entrada BibTeX (estructural).

        Args:
            entrada: Diccionario de entrada

        Returns:
            Tupla de (errores, advertencias)
        """
        errores = []
        advertencias = []

        tipo_entrada = entrada['tipo']
        clave = entrada['clave']
        campos = entrada['campos']

        # Verificar campos requeridos
        if tipo_entrada in self.campos_requeridos:
            for campo_req in self.campos_requeridos[tipo_entrada]:
                if campo_req not in campos or not campos[campo_req]:
                    # Caso especial: book puede tener author O editor
                    if tipo_entrada == 'book' and campo_req == 'author':
                        if 'editor' not in campos or not campos['editor']:
                            errores.append({
                                'tipo': 'campo_requerido_faltante',
                                'campo': 'author o editor',
                                'severidad': 'alta',
                                'mensaje': f'Entrada {clave}: Falta el campo requerido "author" o "editor"'
                            })
                    else:
                        errores.append({
                            'tipo': 'campo_requerido_faltante',
                            'campo': campo_req,
                            'severidad': 'alta',
                            'mensaje': f'Entrada {clave}: Falta el campo requerido "{campo_req}"'
                        })

        # Verificar campos recomendados
        if tipo_entrada in self.campos_recomendados:
            for campo_rec in self.campos_recomendados[tipo_entrada]:
                if campo_rec not in campos or not campos[campo_rec]:
                    advertencias.append({
                        'tipo': 'campo_recomendado_faltante',
                        'campo': campo_rec,
                        'severidad': 'media',
                        'mensaje': f'Entrada {clave}: Falta el campo recomendado "{campo_rec}"'
                    })

        # Validar año
        if 'year' in campos:
            year = campos['year']
            if not re.match(r'^\d{4}$', year):
                errores.append({
                    'tipo': 'year_invalido',
                    'campo': 'year',
                    'valor': year,
                    'severidad': 'alta',
                    'mensaje': f'Entrada {clave}: Formato de año inválido "{year}" (debe ser 4 dígitos)'
                })
            elif int(year) < 1600 or int(year) > 2030:
                advertencias.append({
                    'tipo': 'year_sospechoso',
                    'campo': 'year',
                    'valor': year,
                    'severidad': 'media',
                    'mensaje': f'Entrada {clave}: Año sospechoso "{year}" (fuera del rango razonable)'
                })

        # Validar formato de DOI
        if 'doi' in campos:
            doi = campos['doi']
            if not re.match(r'^10\.\d{4,}/[^\s]+$', doi):
                advertencias.append({
                    'tipo': 'formato_doi_invalido',
                    'campo': 'doi',
                    'valor': doi,
                    'severidad': 'media',
                    'mensaje': f'Entrada {clave}: Formato de DOI inválido "{doi}"'
                })

        # Verificar guion simple en páginas (debe ser --)
        if 'pages' in campos:
            paginas = campos['pages']
            if re.search(r'\d-\d', paginas) and '--' not in paginas:
                advertencias.append({
                    'tipo': 'formato_rango_paginas',
                    'campo': 'pages',
                    'valor': paginas,
                    'severidad': 'baja',
                    'mensaje': f'Entrada {clave}: El rango de páginas usa guion simple, debería usar -- (guion largo)'
                })

        # Verificar formato de autores
        if 'author' in campos:
            autor = campos['author']
            if ';' in autor or '&' in autor:
                errores.append({
                    'tipo': 'formato_autores_invalido',
                    'campo': 'author',
                    'severidad': 'alta',
                    'mensaje': f'Entrada {clave}: Los autores deben separarse con " and ", no ";" ni "&"'
                })

        return errores, advertencias

    def _similitud_texto(self, a: str, b: str) -> float:
        """Calcula similitud difusa entre dos cadenas de texto."""
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    def verificar_doi(self, doi: str, entrada: Dict = None) -> Tuple[bool, Optional[Dict], List[Dict]]:
        """
        Verifica un DOI: resuelve y compara metadatos contra la entrada (Tier C).

        Args:
            doi: Digital Object Identifier
            entrada: Diccionario de entrada BibTeX para comparación (opcional)

        Returns:
            Tupla de (resuelve, metadatos, discrepancias)
        """
        discrepancias = []

        try:
            url = f'https://doi.org/{doi}'
            response = self.session.head(url, timeout=10, allow_redirects=True)

            if response.status_code >= 400:
                return False, None, [{
                    'tipo': 'doi_no_resuelve',
                    'severidad': 'alta',
                    'mensaje': f'El DOI no resuelve: {doi}'
                }]

            # DOI resuelve — obtener metadatos de CrossRef para Tier C
            crossref_url = f'https://api.crossref.org/works/{doi}'
            metadata_response = self.session.get(crossref_url, timeout=10)

            if metadata_response.status_code != 200:
                # Tier B: DOI resuelve pero no hay metadatos CrossRef
                return True, None, []

            data = metadata_response.json()
            message = data.get('message', {})

            # Extraer metadatos clave de CrossRef
            titulo_crossref = message.get('title', [''])[0] if message.get('title') else ''
            year_crossref = self._extraer_year_crossref(message)
            autores_crossref = self._formatear_autores_crossref(message.get('author', []))

            metadatos = {
                'title': titulo_crossref,
                'year': year_crossref,
                'authors': autores_crossref,
            }

            # Tier C: comparar contra la entrada si se proporcionó
            if entrada and entrada.get('campos'):
                campos = entrada['campos']

                # Comparar título (difuso)
                titulo_entrada = campos.get('title', '')
                if titulo_crossref and titulo_entrada:
                    sim = self._similitud_texto(titulo_crossref, titulo_entrada)
                    if sim < self.umbral_titulo:
                        discrepancias.append({
                            'tipo': 'discrepancia_titulo',
                            'severidad': 'alta',
                            'esperado': titulo_crossref[:120],
                            'encontrado': titulo_entrada[:120],
                            'similitud': f'{sim:.2f}',
                            'mensaje': f'Discrepancia de título (similitud {sim:.2f}):\n  CrossRef: {titulo_crossref[:120]}\n  BibTeX:   {titulo_entrada[:120]}'
                        })

                # Comparar año (exacto)
                year_entrada = campos.get('year', '')
                if year_crossref and year_entrada:
                    if year_crossref != year_entrada:
                        discrepancias.append({
                            'tipo': 'discrepancia_year',
                            'severidad': 'alta',
                            'esperado': year_crossref,
                            'encontrado': year_entrada,
                            'mensaje': f'Discrepancia de año: CrossRef={year_crossref}, BibTeX={year_entrada}'
                        })

                # Comparar primer autor (difuso)
                autores_entrada = campos.get('author', '')
                if autores_crossref and autores_entrada:
                    # Comparar solo el primer autor
                    primer_autor_crossref = autores_crossref.split(' and ')[0] if autores_crossref else ''
                    primer_autor_entrada = autores_entrada.split(' and ')[0] if autores_entrada else ''
                    if primer_autor_crossref and primer_autor_entrada:
                        sim_autor = self._similitud_texto(primer_autor_crossref, primer_autor_entrada)
                        if sim_autor < 0.75:
                            discrepancias.append({
                                'tipo': 'discrepancia_autor',
                                'severidad': 'media',
                                'esperado': primer_autor_crossref,
                                'encontrado': primer_autor_entrada,
                                'similitud': f'{sim_autor:.2f}',
                                'mensaje': f'Discrepancia de primer autor (similitud {sim_autor:.2f}): CrossRef="{primer_autor_crossref}", BibTeX="{primer_autor_entrada}"'
                            })

            return True, metadatos, discrepancias

        except Exception:
            return False, None, [{
                'tipo': 'error_verificacion',
                'severidad': 'alta',
                'mensaje': f'Error al verificar el DOI: {doi}'
            }]

    def verificar_url(self, url: str, entrada: Dict = None) -> Tuple[bool, List[Dict]]:
        """
        Verifica una fuente sin DOI: resuelve URL y compara título de página (Tier B).

        Args:
            url: URL de la fuente
            entrada: Diccionario de entrada BibTeX para comparación

        Returns:
            Tupla de (resuelve, discrepancias)
        """
        discrepancias = []

        try:
            response = self.session.get(url, timeout=15, allow_redirects=True, headers={
                'User-Agent': 'ValidadorCitas/2.0 (Herramienta de Gestión de Citas)'
            })

            if response.status_code >= 400:
                return False, [{
                    'tipo': 'url_no_resuelve',
                    'severidad': 'alta',
                    'mensaje': f'La URL no resuelve (HTTP {response.status_code}): {url}'
                }]

            # Tier B: extraer título de la página y comparar
            if entrada and entrada.get('campos'):
                titulo_entrada = entrada['campos'].get('title', '')

                # Buscar <title> en el HTML
                titulo_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE | re.DOTALL)
                if titulo_match:
                    titulo_pagina = titulo_match.group(1).strip()
                    # Limpiar sufijos comunes de sitios web
                    titulo_pagina = re.sub(r'\s*[-|]\s*[^|]+$', '', titulo_pagina).strip()

                    sim = self._similitud_texto(titulo_pagina, titulo_entrada)
                    if sim < self.umbral_titulo:
                        discrepancias.append({
                            'tipo': 'discrepancia_titulo_url',
                            'severidad': 'media',
                            'esperado': titulo_pagina[:120],
                            'encontrado': titulo_entrada[:120],
                            'similitud': f'{sim:.2f}',
                            'mensaje': f'Discrepancia de título de página (similitud {sim:.2f}):\n  Página: {titulo_pagina[:120]}\n  BibTeX: {titulo_entrada[:120]}'
                        })

            return True, discrepancias

        except requests.exceptions.Timeout:
            return False, [{
                'tipo': 'timeout_url',
                'severidad': 'alta',
                'mensaje': f'Tiempo de espera agotado para la URL: {url}'
            }]
        except Exception as e:
            return False, [{
                'tipo': 'error_url',
                'severidad': 'alta',
                'mensaje': f'Error al verificar la URL {url}: {e}'
            }]

    def detectar_duplicados(self, entradas: List[Dict]) -> List[Dict]:
        """
        Detecta entradas duplicadas.

        Args:
            entradas: Lista de diccionarios de entrada

        Returns:
            Lista de grupos duplicados
        """
        duplicados = []

        # Verificar DOIs duplicados
        mapa_doi = defaultdict(list)
        for entrada in entradas:
            doi = entrada['campos'].get('doi', '').strip()
            if doi:
                mapa_doi[doi].append(entrada['clave'])

        for doi, claves in mapa_doi.items():
            if len(claves) > 1:
                duplicados.append({
                    'tipo': 'doi_duplicado',
                    'doi': doi,
                    'entradas': claves,
                    'severidad': 'alta',
                    'mensaje': f'DOI duplicado {doi} encontrado en las entradas: {", ".join(claves)}'
                })

        # Verificar claves de cita duplicadas
        conteo_claves = defaultdict(int)
        for entrada in entradas:
            conteo_claves[entrada['clave']] += 1

        for clave, cantidad in conteo_claves.items():
            if cantidad > 1:
                duplicados.append({
                    'tipo': 'clave_duplicada',
                    'clave': clave,
                    'cantidad': cantidad,
                    'severidad': 'alta',
                    'mensaje': f'La clave de cita "{clave}" aparece {cantidad} veces'
                })

        # Verificar títulos similares (posibles duplicados)
        titulos = {}
        for entrada in entradas:
            titulo = entrada['campos'].get('title', '').lower()
            titulo = re.sub(r'[^\w\s]', '', titulo)  # Quitar puntuación
            titulo = ' '.join(titulo.split())  # Normalizar espacios

            if titulo:
                if titulo in titulos:
                    duplicados.append({
                        'tipo': 'titulo_similar',
                        'entradas': [titulos[titulo], entrada['clave']],
                        'severidad': 'media',
                        'mensaje': f'Posible duplicado: "{titulos[titulo]}" y "{entrada["clave"]}" tienen títulos idénticos'
                    })
                else:
                    titulos[titulo] = entrada['clave']

        return duplicados

    def validar_archivo(self, ruta: str, verificar_dois: bool = False) -> Dict:
        """
        Valida un archivo BibTeX completo.

        Args:
            ruta: Ruta al archivo BibTeX
            verificar_dois: Verificar DOIs con comparación de contenido (Tier C)

        Returns:
            Diccionario con el reporte de validación
        """
        print(f'Parseando {ruta}...', file=sys.stderr)
        entradas = self.parsear_archivo_bibtex(ruta)

        if not entradas:
            return {
                'total_entradas': 0,
                'errores': [],
                'advertencias': [],
                'duplicados': []
            }

        print(f'Encontradas {len(entradas)} entradas', file=sys.stderr)

        todos_errores = []
        todas_advertencias = []

        # Validar cada entrada (estructural)
        for i, entrada in enumerate(entradas):
            print(f'Validando entrada {i+1}/{len(entradas)}: {entrada["clave"]}', file=sys.stderr)
            errores, advertencias = self.validar_entrada(entrada)

            for error in errores:
                error['entrada'] = entrada['clave']
                todos_errores.append(error)

            for advertencia in advertencias:
                advertencia['entrada'] = entrada['clave']
                todas_advertencias.append(advertencia)

        # Verificar duplicados
        print('Verificando duplicados...', file=sys.stderr)
        duplicados = self.detectar_duplicados(entradas)

        # Verificar DOIs y URLs (Tier C + Tier B)
        if verificar_dois:
            print('Verificando DOIs y URLs...', file=sys.stderr)
            for i, entrada in enumerate(entradas):
                doi = entrada['campos'].get('doi', '')
                url = entrada['campos'].get('url', '')

                if doi:
                    print(f'Verificando DOI {i+1}/{len(entradas)}: {doi}', file=sys.stderr)
                    resuelve, metadatos, discrepancias = self.verificar_doi(doi, entrada)

                    if not resuelve:
                        for d in discrepancias:
                            d['entrada'] = entrada['clave']
                            todos_errores.append(d)
                    elif discrepancias:
                        for d in discrepancias:
                            d['entrada'] = entrada['clave']
                            if d['severidad'] == 'alta':
                                todos_errores.append(d)
                            else:
                                todas_advertencias.append(d)

                elif url:
                    print(f'Verificando URL {i+1}/{len(entradas)}: {url[:80]}', file=sys.stderr)
                    resuelve, discrepancias = self.verificar_url(url, entrada)

                    if not resuelve:
                        for d in discrepancias:
                            d['entrada'] = entrada['clave']
                            todos_errores.append(d)
                    elif discrepancias:
                        for d in discrepancias:
                            d['entrada'] = entrada['clave']
                            todas_advertencias.append(d)

        return {
            'archivo': ruta,
            'total_entradas': len(entradas),
            'entradas_validas': len(entradas) - len([e for e in todos_errores if e['severidad'] == 'alta']),
            'errores': todos_errores,
            'advertencias': todas_advertencias,
            'duplicados': duplicados
        }

    def _extraer_year_crossref(self, message: Dict) -> str:
        """Extrae el año desde un mensaje de CrossRef."""
        date_parts = message.get('published-print', {}).get('date-parts', [[]])
        if not date_parts or not date_parts[0]:
            date_parts = message.get('published-online', {}).get('date-parts', [[]])

        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
        return ''

    def _formatear_autores_crossref(self, autores: List[Dict]) -> str:
        """Formatea lista de autores desde CrossRef."""
        if not autores:
            return ''

        formateados = []
        for autor in autores[:3]:  # Primeros 3 autores
            given = autor.get('given', '')
            family = autor.get('family', '')
            if family:
                formateados.append(f'{family}, {given}' if given else family)

        if len(autores) > 3:
            formateados.append('et al.')

        return ', '.join(formateados)


def principal():
    """Interfaz de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Valida archivos BibTeX con verificación de contenido (Tier C)',
        epilog='Ejemplo: python validate_citations.py referencias.bib --check-dois'
    )

    parser.add_argument(
        'archivo',
        help='Archivo BibTeX a validar'
    )

    parser.add_argument(
        '--check-dois',
        action='store_true',
        help='Verificar DOIs con comparación de contenido (Tier C) y URLs (Tier B)'
    )

    parser.add_argument(
        '--report',
        help='Archivo de salida para el reporte JSON de validación'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostrar salida detallada'
    )

    args = parser.parse_args()

    # Validar archivo
    validador = ValidadorCitas()
    reporte = validador.validar_archivo(args.archivo, verificar_dois=args.check_dois)

    # Imprimir resumen
    print('\n' + '=' * 60)
    print('REPORTE DE VALIDACIÓN DE CITAS')
    print('=' * 60)
    print(f'\nArchivo: {args.archivo}')
    print(f'Total de entradas: {reporte["total_entradas"]}')
    print(f'Entradas válidas: {reporte["entradas_validas"]}')
    print(f'Errores: {len(reporte["errores"])}')
    print(f'Advertencias: {len(reporte["advertencias"])}')
    print(f'Duplicados: {len(reporte["duplicados"])}')

    # Imprimir errores
    if reporte['errores']:
        print('\n' + '-' * 60)
        print('ERRORES (debe corregir):')
        print('-' * 60)
        for error in reporte['errores']:
            print(f'\n{error["mensaje"]}')
            if args.verbose:
                print(f'  Tipo: {error["tipo"]}')
                print(f'  Severidad: {error["severidad"]}')

    # Imprimir advertencias
    if reporte['advertencias'] and args.verbose:
        print('\n' + '-' * 60)
        print('ADVERTENCIAS (debería corregir):')
        print('-' * 60)
        for advertencia in reporte['advertencias']:
            print(f'\n{advertencia["mensaje"]}')

    # Imprimir duplicados
    if reporte['duplicados']:
        print('\n' + '-' * 60)
        print('DUPLICADOS:')
        print('-' * 60)
        for dup in reporte['duplicados']:
            print(f'\n{dup["mensaje"]}')

    # Guardar reporte
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        print(f'\nReporte detallado guardado en: {args.report}')

    # Salir con código de error si hay errores
    if reporte['errores']:
        sys.exit(1)


if __name__ == '__main__':
    principal()
