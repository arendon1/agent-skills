---
name: geo-map-svg
description: >-
  Skill de información geográfica y renderizado SVG vectorial. Resuelve
  consultas de ubicación, descarga geometría administrativa + calles +
  parques + cuerpos de agua + edificios vía OSM (Nominatim + Overpass),
  aplica fallback automático a Mapbox cuando OSM falla o devuelve datos
  insuficientes, proyecta a Web Mercator (EPSG:3857) y emite un SVG
  limpio agrupado en <g id="..."> semánticos listos paraAffinity
  Designer, PowerPoint o Illustrator. Usa cuando el usuario pida un mapa
  vectorial editable de una ciudad/barrio/región, un plano de calles,
  un mapa ilustrativo para una presentación o material académico, o
  cuando entregue coordenadas explícitas y necesite un SVG geográficamente
  fiel. Use when the user asks for a vector map, SVG export of a city,
  editable street map, or geographic visualization in SVG form.
invocation: auto
layer: domain
provides: [osm-nominatim, osm-overpass, mapbox-geocoding, web-mercator, svg-export]
language: es-CO
metadata:
  version: "1.0.0"
  author: agent-skills
---

# geo-map-svg

Skill agnóstica que convierte una consulta geográfica (texto o coordenadas)
en un archivo SVG vectorial limpio, agrupado por capas semánticas y
listo para edición visual en herramientas de diseño.

## Principios

1. **Fallback obligatorio de dos capas.** Proveedor principal = OSM (Nominatim +
   Overpass). Respaldo = Mapbox Geocoding. El respaldo se activa sólo si OSM
   falla (timeout, error de red, rate-limit) o devuelve geometría vacía /
   insuficiente para el bounding box solicitado.
2. **Geometría primero, estilo configurable.** El render produce estructura SVG
   editable (jerarquía `<g id="...">`) con paleta por defecto apta para papel
   e impresión. Estilos viven en `LAYER_STYLES` del script — modificar no rompe
   la jerarquía.
3. **Web Mercator (EPSG:3857).** Coordenadas esféricas se proyectan al plano
   cartesiano antes del render. El _bounding box_ se ajusta automáticamente
   al lienzo conservando proporciones (escala uniforme = `min(availW/geoW,
   availH/geoH)`).
4. **Salida JSON estable.** Toda ejecución retorna un objeto con `status`,
   `provider_used`, `metadata` y `svg_raw` (string SVG completo). Consumidores
   pueden extraer el SVG sin re-procesar.
5. **Agnóstica del harness.** Sólo ejecuta un script Python vía shell. Sin
   dependencias de proveedor de modelos, sin nombres de herramientas del
   harness en el cuerpo.

## Preflight

Dependencias del script (todas en stdlib excepto ninguna — el script no
requiere paquetes externos en tiempo de ejecución; sólo `python3 >= 3.9`):

```bash
# Verificar Python
python3 --version    # >= 3.9 recomendado

# Verificar conectividad OSM (opcional, sanity check)
python3 -c "import urllib.request; print('ok')"
```

Para el fallback a Mapbox se requiere la variable de entorno `MAPBOX_TOKEN`
o el flag `--mapbox-token`. Sin token, OSM es el único proveedor y los
fallos no se recuperan.

## Flujo de trabajo

### 1. Entrada

Acepta:

- Texto libre: `"Floridablanca, Santander"`, `"Bogotá D.C."`, `"Medellín"`.
- Coordenadas explícitas: `"7.0625,-73.0856"` (lat,lon).

### 2. Resolución geográfica (Capa 1 = OSM)

```python
# Paso interno del script
result = nominatim_search(query)        # Nominatim API
bbox   = expand_bbox(result["boundingbox"])
data   = overpass_query(bbox)           # Overpass QL — ways y nodes
features = parse_overpass(data)         # clasifica por tags
```

Criterio de éxito OSM: bbox + ≥1 elemento geométrico. Si `features == []`
o Nominatim/Overpass lanza excepción → activar fallback.

### 3. Fallback (Capa 2 = Mapbox)

```python
if not features and MAPBOX_TOKEN:
    res = mapbox_search(query, MAPBOX_TOKEN)
    # emite marcador central + bbox por defecto si Mapbox responde
```

El fallback a Mapbox **NO** descarga geometría vectorial (no es un servicio
Overpass equivalente); produce un punto central y bounding box aproximado.
Si el usuario necesita geometría completa y OSM cae, se debe reintentar OSM
o usar un servicio de tiles vectoriales.

### 4. Proyección Web Mercator

```python
x, y = project_web_mercator(lon, lat)
# x,y en metros; se ajusta al lienzo con fit_to_canvas()
```

Límite: |lat| ≤ 85.05112878° (proyección se trunca fuera de este rango,
igual que cualquier implementación Mercator estándar).

### 5. Render SVG con capas semánticas

Cada feature se clasifica en una capa semántica. El render emite las capas
en orden back-to-front:

| `id` del `<g>`            | Estilo por defecto           | Contenido típico                       |
|---------------------------|------------------------------|----------------------------------------|
| `limites-administrativos` | stroke marrón, sin fill      | Fronteras municipales / departamentales |
| `cuerpos-de-agua`         | fill azul claro              | Ríos, lagos, embalses                  |
| `parques-y-zonas-verdes`  | fill verde claro             | Parques, reservas                      |
| `edificios`               | fill beige translúcido       | Manzanas edificadas                    |
| `calles-principales`      | stroke ocre                  | Vías motorway/trunk/primary/secondary  |
| `puntos-de-interes`       | círculo rojo                 | Ciudades, pueblos, marcadores          |

El SVG resultante es válido, incluye `viewBox` dinámico, está indentado y
no contiene elementos huérfanos. Cada `<g>` se puede colapsar/expandir y
recolorear de forma independiente en cualquier editor vectorial.

## Uso

### CLI

```bash
# Render básico (sólo OSM)
python3 domain/geo-map-svg/scripts/geo_map_svg.py \
    "Floridablanca, Santander" \
    --width 800 --height 600 \
    --out floridablanca.svg

# Con fallback a Mapbox
MAPBOX_TOKEN=pk.xxx \
python3 domain/geo-map-svg/scripts/geo_map_svg.py \
    "Bogotá" --out bogota.svg

# Sólo imprimir JSON de metadata (sin guardar archivo)
python3 domain/geo-map-svg/scripts/geo_map_svg.py "Medellín"
```

### Como módulo Python

```python
import sys
sys.path.insert(0, "domain/geo-map-svg/scripts")
from geo_map_svg import generate_map

result = generate_map(
    query="Floridablanca, Santander",
    width=1000,
    height=800,
    mapbox_token=None,           # o str token
)
assert result["status"] == "success"
svg_string = result["svg_raw"]
```

## Esquema de salida

```json
{
  "status": "success | error",
  "provider_used": "osm | mapbox | none",
  "metadata": {
    "center_coords": [lat, lon],
    "bounding_box": [min_lon, min_lat, max_lon, max_lat],
    "dimensions": { "width": 800, "height": 600 }
  },
  "svg_raw": "<svg ...>...</svg>",
  "svg_path": "/abs/path/to/file.svg"   // presente si --out
}
```

En caso de error total (sin OSM, sin Mapbox, sin token):

```json
{
  "status": "error",
  "error": "<motivo>",
  "provider_used": "none"
}
```

## Criterios de aceptación

| # | Criterio | Validación |
|---|----------|------------|
| 1 | Fallback OSM → Mapbox transparente | Apagar red OSM y verificar que Mapbox se activa sin excepción crítica |
| 2 | Proporciones geográficas fieles | `geoW * scale == availW` o `geoH * scale == availH` (aspect ratio uniforme) |
| 3 | SVG editable | Cada categoría en `<g id="...">` único; abrir enAffinity/PowerPoint y desagrupar sin errores |
| 4 | SVG sin distorsión | `viewBox` dinámico; sin estiramiento vertical/horizontal |
| 5 | Sin elementos huérfanos | Todos los `<path>`, `<circle>` están dentro de un `<g>` con `id` válido |

## Estructura interna

```
domain/geo-map-svg/
├── SKILL.md
├── scripts/
│   └── geo_map_svg.py        # CLI + API Python
├── references/
│   └── web-mercator.md       # matemática de la proyección
├── examples/
│   └── colombia-floridablanca.md
└── evals/
    └── smoke.py              # test offline de proyección y SVG
```

## Notas operativas

- **Rate limit Nominatim:** 1 req/s. El script serializa y respeta el
  `User-Agent`; en flujos de alto volumen añadir `time.sleep(1.1)` entre
  invocaciones (no incluido por defecto — es responsabilidad del caller).
- **Rate limit Overpass:** variable según endpoint; se prueban 2 servidores
  en secuencia (overpass-api.de → overpass.kumi.systems).
- **Idiomas:** la skill responde en es-CO; los tags OSM consultados son los
  oficiales en inglés (`highway`, `building`, `natural`, etc.) — esos nombres
  no se localizan.
- **Privacidad:** Nominatim exige `User-Agent` identificable. El script envía
  `agent-skills/geo-map-svg/1.0` por defecto.