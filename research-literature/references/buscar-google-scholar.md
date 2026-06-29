# Buscar en Google Scholar (manual)

Guía de estrategias de búsqueda manual en Google Scholar. A diferencia de EXA y
Semantic Scholar, Google Scholar no tiene API oficial. El agente debe realizar
la búsqueda usando búsqueda web y aplicar las estrategias aquí documentadas.

## Cuándo usar Google Scholar

- **Último recurso**: cuando EXA y Semantic Scholar no devuelven resultados suficientes
- **Cobertura máxima**: Google Scholar indexa fuentes que las APIs académicas no cubren
  (tesis, patentes, libros, informes técnicos, preprints en repositorios pequeños)
- **Búsqueda de citas**: encontrar quién cita un paper específico (cited by)
- **Perfiles de autor**: buscar el perfil completo de un investigador

## Operadores de búsqueda

Google Scholar soporta operadores avanzados en la barra de búsqueda:

| Operador | Sintaxis | Ejemplo |
|----------|----------|---------|
| Autor | `author:"apellido"` | `author:"Hinton"` |
| Título | `intitle:"frase"` | `intitle:"deep learning"` |
| Fuente | `source:"journal"` | `source:"Nature"` |
| Frase exacta | `"frase exacta"` | `"reinforcement learning"` |
| Exclusión | `-término` | `-survey -review` |
| Año | Usar filtro lateral | Rango personalizado en la UI |

### Combinación de operadores

```
author:"Vaswani" intitle:"attention" source:"NeurIPS"
```

Busca papers de Vaswani con "attention" en el título publicados en NeurIPS.

## Estrategias de búsqueda

### 1. Búsqueda exploratoria por tema

1. Escribir el tema de investigación como frase natural o palabras clave
2. Usar el filtro de año en la barra lateral para limitar a un rango
3. Ordenar por relevancia (default) o por fecha
4. Revisar los primeros 20-30 resultados
5. Para cada paper relevante, anotar: título, autores, año, DOI (si está), URL de Google Scholar

### 2. Búsqueda por autor seminal

Cuando se conoce un autor clave en el campo:

```
author:"Bengio" "deep learning"
```

Limitar por año para encontrar sus trabajos más recientes o más citados.

### 3. Búsqueda por revista o conferencia

```
source:"Journal of Machine Learning Research" "graph neural networks"
```

### 4. Seguimiento de citas (cited by)

1. Encontrar un paper seminal en el tema
2. Usar el enlace "Cited by N" para ver quién lo ha citado
3. Filtrar los citing papers por año para encontrar trabajos recientes
4. Buscar dentro de los citing papers con "Search within citing articles"

## Extracción de metadatos

Google Scholar no expone metadatos estructurados consistentemente. Estrategia para
extraerlos:

1. **DOI**: hacer clic en el título del paper. Muchos papers listan el DOI en la página
   de destino (journal, arXiv, etc.)
2. **Autores**: visibles directamente en el resultado de búsqueda
3. **Año**: visible en el resultado de búsqueda (línea inferior: "2024 - Journal of...")
4. **Abstract**: hacer clic en el título y buscar el abstract en la página de destino,
   o usar Semantic Scholar con `--match` para obtenerlo
5. **Citas**: número visible en el resultado ("Cited by 123")

## Limitaciones

- **No hay API**: la búsqueda es manual y depende del criterio del agente
- **Metadatos inconsistentes**: los resultados pueden carecer de DOI, abstract o
  información completa de venue
- **Sesgo de citas**: los papers muy citados dominan los resultados; papers nuevos
  o de nicho pueden quedar enterrados
- **Sin filtros programáticos**: no se puede filtrar por tipo de publicación, peer
  review, o acceso abierto
- **Rate limiting implícito**: búsquedas muy rápidas pueden activar CAPTCHA

## Recomendación

Google Scholar debe usarse como **complemento de verificación**, no como fuente primaria.
El flujo ideal:

1. Buscar en EXA → obtener DOIs y URLs
2. Complementar con Semantic Scholar → metadatos ricos, verificación por título
3. Si los resultados son insuficientes (tema muy específico, literatura gris), usar
   Google Scholar para encontrar fuentes adicionales
4. Para cada fuente encontrada en Google Scholar, verificar el DOI con Semantic Scholar
   o CrossRef antes de entregarla a `generar-paper`
