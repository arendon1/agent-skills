# SPEC: Geo-Information & SVG Mapping Skill

## 1. Objetivo General

Diseñar e implementar una habilidad (skill) para el agente que le permita
interactuar con APIs geográficas para obtener coordenadas, límites
administrativos y vectores de calles, procesar dicha información y exportar
mapas vectoriales precisos en formato SVG.

## 2. Arquitectura de Integración (Estrategia Fallback)

La skill implementa un flujo de consulta secuencial de dos capas para
garantizar la disponibilidad y calidad de los datos:

- **Proveedor Principal (Capa 1): OpenStreetMap (OSM)**
  - **Geocodificación:** Nominatim API.
  - **Geometrías/Vectores:** Overpass API (consultas Overpass QL).
  - **Criterio de éxito:** Si el resultado es exitoso, contiene datos
    geométricos válidos y tiene un score de confianza aceptable, se procesa.
- **Proveedor de Respaldo (Capa 2): Mapbox**
  - **Activación:** Se invoca únicamente si OSM falla (timeout, error de
    red), excede sus límites de ratio de peticiones, o devuelve un set de
    datos vacío/insuficiente para el área solicitada.
  - **Servicio:** Mapbox Geocoding API.

## 3. Flujo de Trabajo Técnico

1. **Entrada:** Recibe el texto o query con la ubicación deseada.
2. **Consulta Principal (OSM):** Se intentan extraer los datos geográficos
   de OpenStreetMap.
   - _Si es exitoso:_ Envía el GeoJSON directamente al pipeline de
     procesamiento.
   - _Si falla o retorna vacío:_ Se activa de inmediato el fallback hacia
     la API de Mapbox.
3. **Proyección Cartográfica:** Transforma las coordenadas esféricas del
   GeoJSON obtenido en coordenadas cartesianas (X, Y) usando Web Mercator.
4. **Renderizado:** Traduce los datos proyectados a etiquetas vectoriales
   organizadas y genera el archivo SVG final.

### Paso 1: Geocodificación y Extracción de Datos

- **Input:** Un string con la ubicación (ej. "Floridablanca, Santander")
  o coordenadas explícitas.
- **Output esperado:** Un objeto estructurado en formato **GeoJSON** que
  contenga nodos (puntos de interés), _ways_ (calles, carreteras) y
  relaciones (límites de polígonos).

### Paso 2: Normalización y Proyección Cartográfica

El agente debe tomar las coordenadas geográficas esféricas `[Longitud,
Latitud]` del GeoJSON y proyectarlas en un plano bidimensional cartesiano
`(X, Y)` utilizando la **Proyección Web Mercator (EPSG:3857)** adaptada
al tamaño del lienzo SVG requerido.

- Debe calcular automáticamente el _Bounding Box_ (caja de delimitación)
  para centrar y escalar el contenido de manera óptima dentro del lienzo.

### Paso 3: Renderizado a SVG Vectorial (Requerimiento CORE de Estructura)

La skill debe mapear las entidades geográficas a etiquetas SVG válidas. Es
un **requerimiento estrictamente mandatorio** que todos los elementos se
organicen en grupos (`<g>`) perfectamente nombrados e identificados. Esto
garantiza la comprensión humana directa y permite que el SVG sea importado
y editado como un recurso de diseño limpio en herramientas como
**Affinity Designer** o **Microsoft PowerPoint**.

- **Organización por Capas Semánticas:** Cada categoría de datos debe estar
  agrupada dentro de una etiqueta `<g>` con un atributo `id` semántico,
  claro y legible (ej. `<g id="limites-administrativos">`,
  `<g id="calles-principales">`, `<g id="parques-y-zonas-verdes">`,
  `<g id="cuerpos-de-agua">`).
- **Elementos de Línea:** `LineString` y `MultiLineString` (calles, ríos)
  -> Elementos `<path d="..." />` con atributos de estilo configurables
  (`stroke`, `stroke-width`).
- **Elementos de Polígono:** `Polygon` y `MultiPolygon` (edificios,
  parques, zonas urbanas) -> Elementos `<path d="..." />` con atributos
  `fill` y `opacity`.
- **Elementos de Punto:** `Point` (marcadores o lugares clave) -> Elementos
  `<circle cx="..." cy="..." />`.

## 4. Requisitos del Output del Script/Función

Cualquier ejecución de esta skill debe retornar un objeto JSON con la
siguiente estructura:

```json
{
  "status": "success",
  "provider_used": "osm" | "mapbox",
  "metadata": {
    "center_coords": [lat, lon],
    "bounding_box": [min_lon, min_lat, max_lon, max_lat],
    "dimensions": { "width": 800, "height": 600 }
  },
  "svg_raw": "<svg ...>...</svg>"
}
```

## 5. Criterios de Aceptación para el Agente

- **Validación de Fallback:** Si se simula un error de conexión con
  Nominatim/Overpass, la skill debe cambiar automáticamente a Mapbox sin
  lanzar excepciones críticas de detención.
- **Precisión Geométrica:** Las proporciones espaciales del mapa en el
  SVG resultante deben mantenerse fieles a la realidad geográfica,
  evitando distorsiones visuales severas (estiramiento
  vertical/horizontal).
- **Código SVG Limpio y Editable:** El string de SVG generado debe estar
  bien indentado, incluir una etiqueta `viewBox` dinámica, no contener
  elementos huérfanos y, sobre todo, exhibir una jerarquía de capas
  (`id` en etiquetas `<g>`) completamente intuitiva para que un humano
  pueda desagrupar y cambiar colores de calles o zonas de forma
  independiente en su software de diseño.

## 6. Restricciones del Harness

- Skill agnóstica (§9): sin referencias a harnesses o herramientas
  específicas en el cuerpo del SKILL.md.
- Idioma del skill: `es-CO` (la spec original está en es-CO).
- Capa: `domain`. Invocación: `auto`. `provides`: capacidades
  declaradas.
- Tamaño: `SKILL.md <= 500` líneas.