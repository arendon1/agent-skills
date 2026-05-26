import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from browser_api import get_navegador, get_page_content
from bs4 import BeautifulSoup

navegador = get_navegador()
navegador('https://aulavirtual.uniremington.edu.co/mod/page/view.php?id=477352')
html = get_page_content()

# Simular extraer_modulo_page
soup = BeautifulSoup(html, 'lxml')
region = soup.select_one('#region-main, .course-content, .activity-content')
contenido_html = str(region) if region else html

# Guardar HTML para inspeccionar
with open('debug_profesor.html', 'w', encoding='utf-8') as f:
    f.write(contenido_html)

from extractor_foro import extraer_nombre_profesor
nombre = extraer_nombre_profesor(contenido_html)
print('Nombre detectado:', nombre)

# Debug: buscar tabla con Nombre Completo
soup2 = BeautifulSoup(contenido_html, 'lxml')
for table in soup2.find_all('table'):
    for row in table.find_all('tr'):
        celdas = row.find_all(['td', 'th'])
        for cell in celdas:
            texto = cell.get_text(strip=True)
            if 'nombre' in texto.lower():
                print('ENCONTRADO:', repr(texto))
                print('  siguiente celda:', repr(celdas[celdas.index(cell)+1].get_text(strip=True)) if celdas.index(cell)+1 < len(celdas) else 'N/A')
