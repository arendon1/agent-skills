#!/usr/bin/env python3
"""
Extractor de Metadatos
Extrae metadatos de citas desde DOI, PMID, arXiv ID o URL usando varias APIs.
"""

import sys
import os
import requests
import argparse
import time
import re
import json
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse

class ExtractorMetadatos:
    """Extrae metadatos desde diversas fuentes y genera BibTeX."""

    def __init__(self, email: Optional[str] = None):
        """
        Inicializa el extractor.

        Args:
            email: Correo para la API de Entrez (recomendado para PubMed)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ExtractorMetadatos/2.0 (Herramienta de Gestión de Citas)'
        })
        self.email = email or os.getenv('NCBI_EMAIL', '')

    def identificar_tipo(self, identificador: str) -> Tuple[str, str]:
        """
        Identifica el tipo de identificador.

        Args:
            identificador: DOI, PMID, arXiv ID o URL

        Returns:
            Tupla de (tipo, identificador_limpio)
        """
        identificador = identificador.strip()

        # Verificar si es URL
        if identificador.startswith('http://') or identificador.startswith('https://'):
            return self._parsear_url(identificador)

        # Verificar DOI
        if identificador.startswith('10.'):
            return ('doi', identificador)

        # Verificar arXiv ID
        if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', identificador):
            return ('arxiv', identificador)
        if identificador.startswith('arXiv:'):
            return ('arxiv', identificador.replace('arXiv:', ''))

        # Verificar PMID (número de 8 dígitos típicamente)
        if identificador.isdigit() and len(identificador) >= 7:
            return ('pmid', identificador)

        # Verificar PMCID
        if identificador.upper().startswith('PMC') and identificador[3:].isdigit():
            return ('pmcid', identificador.upper())

        return ('desconocido', identificador)

    def _parsear_url(self, url: str) -> Tuple[str, str]:
        """Parsea una URL para extraer tipo y valor del identificador."""
        parsed = urlparse(url)

        # URLs de DOI
        if 'doi.org' in parsed.netloc:
            doi = parsed.path.lstrip('/')
            return ('doi', doi)

        # URLs de PubMed
        if 'pubmed.ncbi.nlm.nih.gov' in parsed.netloc or 'ncbi.nlm.nih.gov/pubmed' in url:
            pmid = re.search(r'/(\d+)', parsed.path)
            if pmid:
                return ('pmid', pmid.group(1))

        # URLs de arXiv
        if 'arxiv.org' in parsed.netloc:
            arxiv_id = re.search(r'/abs/(\d{4}\.\d{4,5})', parsed.path)
            if arxiv_id:
                return ('arxiv', arxiv_id.group(1))

        # Nature, Science, Cell, etc. — intentar extraer DOI de la URL
        doi_match = re.search(r'10\.\d{4,}/[^\s/]+', url)
        if doi_match:
            return ('doi', doi_match.group())

        return ('url', url)

    def extraer_desde_doi(self, doi: str) -> Optional[Dict]:
        """
        Extrae metadatos desde un DOI usando la API de CrossRef.

        Args:
            doi: Digital Object Identifier

        Returns:
            Diccionario de metadatos o None
        """
        url = f'https://api.crossref.org/works/{doi}'

        try:
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                message = data.get('message', {})

                metadatos = {
                    'tipo_fuente': 'doi',
                    'tipo_entrada': self._tipo_crossref_a_bibtex(message.get('type')),
                    'doi': doi,
                    'title': message.get('title', [''])[0],
                    'authors': self._formatear_autores_crossref(message.get('author', [])),
                    'year': self._extraer_year_crossref(message),
                    'journal': message.get('container-title', [''])[0] if message.get('container-title') else '',
                    'volume': str(message.get('volume', '')) if message.get('volume') else '',
                    'issue': str(message.get('issue', '')) if message.get('issue') else '',
                    'pages': message.get('page', ''),
                    'publisher': message.get('publisher', ''),
                    'url': f'https://doi.org/{doi}'
                }

                return metadatos
            else:
                print(f'Error: La API de CrossRef devolvió estado {response.status_code} para el DOI: {doi}', file=sys.stderr)
                return None

        except Exception as e:
            print(f'Error al extraer metadatos del DOI {doi}: {e}', file=sys.stderr)
            return None

    def extraer_desde_pmid(self, pmid: str) -> Optional[Dict]:
        """
        Extrae metadatos desde un PMID usando PubMed E-utilities.

        Args:
            pmid: PubMed ID

        Returns:
            Diccionario de metadatos o None
        """
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml',
            'rettype': 'abstract'
        }

        if self.email:
            params['email'] = self.email

        api_key = os.getenv('NCBI_API_KEY')
        if api_key:
            params['api_key'] = api_key

        try:
            response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 200:
                root = ET.fromstring(response.content)
                article = root.find('.//PubmedArticle')

                if article is None:
                    print(f'Error: No se encontró artículo para el PMID: {pmid}', file=sys.stderr)
                    return None

                # Extraer metadatos del XML
                medline_citation = article.find('.//MedlineCitation')
                article_elem = medline_citation.find('.//Article')
                journal = article_elem.find('.//Journal')

                # Obtener DOI si está disponible
                doi = None
                article_ids = article.findall('.//ArticleId')
                for article_id in article_ids:
                    if article_id.get('IdType') == 'doi':
                        doi = article_id.text
                        break

                metadatos = {
                    'tipo_fuente': 'pmid',
                    'tipo_entrada': 'article',
                    'pmid': pmid,
                    'title': article_elem.findtext('.//ArticleTitle', ''),
                    'authors': self._formatear_autores_pubmed(article_elem.findall('.//Author')),
                    'year': self._extraer_year_pubmed(article_elem),
                    'journal': journal.findtext('.//Title', ''),
                    'volume': journal.findtext('.//JournalIssue/Volume', ''),
                    'issue': journal.findtext('.//JournalIssue/Issue', ''),
                    'pages': article_elem.findtext('.//Pagination/MedlinePgn', ''),
                    'doi': doi
                }

                return metadatos
            else:
                print(f'Error: La API de PubMed devolvió estado {response.status_code} para el PMID: {pmid}', file=sys.stderr)
                return None

        except Exception as e:
            print(f'Error al extraer metadatos del PMID {pmid}: {e}', file=sys.stderr)
            return None

    def extraer_desde_arxiv(self, arxiv_id: str) -> Optional[Dict]:
        """
        Extrae metadatos desde un arXiv ID usando la API de arXiv.

        Args:
            arxiv_id: Identificador de arXiv

        Returns:
            Diccionario de metadatos o None
        """
        url = 'http://export.arxiv.org/api/query'
        params = {
            'id_list': arxiv_id,
            'max_results': 1
        }

        try:
            response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 200:
                # Parsear XML Atom
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}

                entry = root.find('atom:entry', ns)
                if entry is None:
                    print(f'Error: No se encontró entrada para el arXiv ID: {arxiv_id}', file=sys.stderr)
                    return None

                # Extraer DOI si está publicado
                doi_elem = entry.find('arxiv:doi', ns)
                doi = doi_elem.text if doi_elem is not None else None

                # Extraer referencia de revista si está publicado
                journal_ref_elem = entry.find('arxiv:journal_ref', ns)
                journal_ref = journal_ref_elem.text if journal_ref_elem is not None else None

                # Obtener fecha de publicación
                published = entry.findtext('atom:published', '', ns)
                year = published[:4] if published else ''

                # Obtener autores
                autores = []
                for author in entry.findall('atom:author', ns):
                    name = author.findtext('atom:name', '', ns)
                    if name:
                        autores.append(name)

                metadatos = {
                    'tipo_fuente': 'arxiv',
                    'tipo_entrada': 'misc' if not doi else 'article',
                    'arxiv_id': arxiv_id,
                    'title': entry.findtext('atom:title', '', ns).strip().replace('\n', ' '),
                    'authors': ' and '.join(autores),
                    'year': year,
                    'doi': doi,
                    'journal_ref': journal_ref,
                    'abstract': entry.findtext('atom:summary', '', ns).strip().replace('\n', ' '),
                    'url': f'https://arxiv.org/abs/{arxiv_id}'
                }

                return metadatos
            else:
                print(f'Error: La API de arXiv devolvió estado {response.status_code} para el ID: {arxiv_id}', file=sys.stderr)
                return None

        except Exception as e:
            print(f'Error al extraer metadatos de arXiv {arxiv_id}: {e}', file=sys.stderr)
            return None

    def metadatos_a_bibtex(self, metadatos: Dict, clave_cita: Optional[str] = None) -> str:
        """
        Convierte un diccionario de metadatos a formato BibTeX.

        Args:
            metadatos: Diccionario de metadatos
            clave_cita: Clave de cita personalizada opcional

        Returns:
            Cadena BibTeX
        """
        if not clave_cita:
            clave_cita = self._generar_clave_cita(metadatos)

        tipo_entrada = metadatos.get('tipo_entrada', 'misc')

        # Construir entrada BibTeX
        lineas = [f'@{tipo_entrada}{{{clave_cita},']

        # Agregar campos
        if metadatos.get('authors'):
            lineas.append(f'  author  = {{{metadatos["authors"]}}},')

        if metadatos.get('title'):
            # Proteger mayúsculas
            titulo = self._proteger_titulo(metadatos['title'])
            lineas.append(f'  title   = {{{titulo}}},')

        if tipo_entrada == 'article' and metadatos.get('journal'):
            lineas.append(f'  journal = {{{metadatos["journal"]}}},')
        elif tipo_entrada == 'misc' and metadatos.get('tipo_fuente') == 'arxiv':
            lineas.append(f'  howpublished = {{arXiv}},')

        if metadatos.get('year'):
            lineas.append(f'  year    = {{{metadatos["year"]}}},')

        if metadatos.get('volume'):
            lineas.append(f'  volume  = {{{metadatos["volume"]}}},')

        if metadatos.get('issue'):
            lineas.append(f'  number  = {{{metadatos["issue"]}}},')

        if metadatos.get('pages'):
            pages = metadatos['pages'].replace('-', '--')  # Guion largo
            lineas.append(f'  pages   = {{{pages}}},')

        if metadatos.get('doi'):
            lineas.append(f'  doi     = {{{metadatos["doi"]}}},')
        elif metadatos.get('url'):
            lineas.append(f'  url     = {{{metadatos["url"]}}},')

        if metadatos.get('pmid'):
            lineas.append(f'  note    = {{PMID: {metadatos["pmid"]}}},')

        if metadatos.get('tipo_fuente') == 'arxiv' and not metadatos.get('doi'):
            lineas.append(f'  note    = {{Preprint}},')

        # Quitar coma final del último campo
        if lineas[-1].endswith(','):
            lineas[-1] = lineas[-1][:-1]

        lineas.append('}')

        return '\n'.join(lineas)

    def _tipo_crossref_a_bibtex(self, tipo_crossref: str) -> str:
        """Mapea tipo de CrossRef a tipo de entrada BibTeX."""
        mapa_tipos = {
            'journal-article': 'article',
            'book': 'book',
            'book-chapter': 'incollection',
            'proceedings-article': 'inproceedings',
            'posted-content': 'misc',
            'dataset': 'misc',
            'report': 'techreport'
        }
        return mapa_tipos.get(tipo_crossref, 'misc')

    def _formatear_autores_crossref(self, autores: List[Dict]) -> str:
        """Formatea lista de autores desde datos de CrossRef."""
        if not autores:
            return ''

        formateados = []
        for autor in autores:
            given = autor.get('given', '')
            family = autor.get('family', '')
            if family:
                if given:
                    formateados.append(f'{family}, {given}')
                else:
                    formateados.append(family)

        return ' and '.join(formateados)

    def _formatear_autores_pubmed(self, autores: List) -> str:
        """Formatea lista de autores desde XML de PubMed."""
        formateados = []
        for autor in autores:
            last_name = autor.findtext('.//LastName', '')
            fore_name = autor.findtext('.//ForeName', '')
            if last_name:
                if fore_name:
                    formateados.append(f'{last_name}, {fore_name}')
                else:
                    formateados.append(last_name)

        return ' and '.join(formateados)

    def _extraer_year_crossref(self, message: Dict) -> str:
        """Extrae el año desde un mensaje de CrossRef."""
        # Intentar published-print primero, luego published-online
        date_parts = message.get('published-print', {}).get('date-parts', [[]])
        if not date_parts or not date_parts[0]:
            date_parts = message.get('published-online', {}).get('date-parts', [[]])

        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
        return ''

    def _extraer_year_pubmed(self, article: ET.Element) -> str:
        """Extrae el año desde XML de PubMed."""
        year = article.findtext('.//Journal/JournalIssue/PubDate/Year', '')
        if not year:
            medline_date = article.findtext('.//Journal/JournalIssue/PubDate/MedlineDate', '')
            if medline_date:
                year_match = re.search(r'\d{4}', medline_date)
                if year_match:
                    year = year_match.group()
        return year

    def _generar_clave_cita(self, metadatos: Dict) -> str:
        """Genera una clave de cita a partir de los metadatos."""
        # Obtener apellido del primer autor
        autores = metadatos.get('authors', '')
        if autores:
            primer_autor = autores.split(' and ')[0]
            if ',' in primer_autor:
                apellido = primer_autor.split(',')[0].strip()
            else:
                apellido = primer_autor.split()[-1] if primer_autor else 'Unknown'
        else:
            apellido = 'Unknown'

        # Obtener año
        year = metadatos.get('year', '').strip()
        if not year:
            year = 'XXXX'

        # Limpiar apellido (quitar caracteres especiales)
        apellido = re.sub(r'[^a-zA-Z]', '', apellido)

        # Obtener palabra clave del título
        titulo = metadatos.get('title', '')
        palabras = re.findall(r'\b[a-zA-Z]{4,}\b', titulo)
        palabra_clave = palabras[0].lower() if palabras else 'paper'

        return f'{apellido}{year}{palabra_clave}'

    def _proteger_titulo(self, titulo: str) -> str:
        """Protege mayúsculas en el título para BibTeX."""
        palabras_protegidas = [
            'DNA', 'RNA', 'CRISPR', 'COVID', 'HIV', 'AIDS', 'AlphaFold',
            'Python', 'AI', 'ML', 'GPU', 'CPU', 'USA', 'UK', 'EU'
        ]

        for palabra in palabras_protegidas:
            titulo = re.sub(rf'\b{palabra}\b', f'{{{palabra}}}', titulo, flags=re.IGNORECASE)

        return titulo

    def extraer(self, identificador: str) -> Optional[str]:
        """
        Extrae metadatos y devuelve BibTeX.

        Args:
            identificador: DOI, PMID, arXiv ID o URL

        Returns:
            Cadena BibTeX o None
        """
        tipo_id, id_limpio = self.identificar_tipo(identificador)

        print(f'Identificado como {tipo_id}: {id_limpio}', file=sys.stderr)

        metadatos = None

        if tipo_id == 'doi':
            metadatos = self.extraer_desde_doi(id_limpio)
        elif tipo_id == 'pmid':
            metadatos = self.extraer_desde_pmid(id_limpio)
        elif tipo_id == 'arxiv':
            metadatos = self.extraer_desde_arxiv(id_limpio)
        else:
            print(f'Error: Tipo de identificador desconocido: {identificador}', file=sys.stderr)
            return None

        if metadatos:
            return self.metadatos_a_bibtex(metadatos)
        else:
            return None


def principal():
    """Interfaz de línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Extrae metadatos de citas desde DOI, PMID, arXiv ID o URL',
        epilog='Ejemplo: python extract_metadata.py --doi 10.1038/s41586-021-03819-2'
    )

    parser.add_argument('--doi', help='Digital Object Identifier')
    parser.add_argument('--pmid', help='PubMed ID')
    parser.add_argument('--arxiv', help='arXiv ID')
    parser.add_argument('--url', help='URL del artículo')
    parser.add_argument('-i', '--input', help='Archivo de entrada con identificadores (uno por línea)')
    parser.add_argument('-o', '--output', help='Archivo de salida para BibTeX (por defecto: stdout)')
    parser.add_argument('--format', choices=['bibtex', 'json'], default='bibtex', help='Formato de salida')
    parser.add_argument('--email', help='Correo para NCBI E-utilities (recomendado)')

    args = parser.parse_args()

    # Recolectar identificadores
    identificadores = []
    if args.doi:
        identificadores.append(args.doi)
    if args.pmid:
        identificadores.append(args.pmid)
    if args.arxiv:
        identificadores.append(args.arxiv)
    if args.url:
        identificadores.append(args.url)

    if args.input:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                ids_archivo = [line.strip() for line in f if line.strip()]
                identificadores.extend(ids_archivo)
        except Exception as e:
            print(f'Error al leer el archivo de entrada: {e}', file=sys.stderr)
            sys.exit(1)

    if not identificadores:
        parser.print_help()
        sys.exit(1)

    # Extraer metadatos
    extractor = ExtractorMetadatos(email=args.email)
    entradas_bibtex = []

    for i, identificador in enumerate(identificadores):
        print(f'\nProcesando {i+1}/{len(identificadores)}...', file=sys.stderr)
        bibtex = extractor.extraer(identificador)
        if bibtex:
            entradas_bibtex.append(bibtex)

        # Límite de tasa
        if i < len(identificadores) - 1:
            time.sleep(0.5)

    if not entradas_bibtex:
        print('Error: No hubo extracciones exitosas', file=sys.stderr)
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
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(salida)
        print(f'\nSe escribieron {len(entradas_bibtex)} entradas en {args.output}', file=sys.stderr)
    else:
        print(salida)

    print(f'\nExtraídas {len(entradas_bibtex)}/{len(identificadores)} entradas', file=sys.stderr)


if __name__ == '__main__':
    principal()
