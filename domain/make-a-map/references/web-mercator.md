# Web Mercator (EPSG:3857) — Notas técnicas

## Definición

Web Mercator (oficialmente EPSG:3857, también conocido como WGS84 / Pseudo-Mercator)
es la proyección cilíndrica conforme utilizada por la práctica totalidad de
servicios de mapas web (Google Maps, OSM, Mapbox, Bing).

A diferencia del Mercator "geográfico" (EPSG:4326 tratado como cilíndrico),
Web Mercator trata la Tierra como una esfera perfecta de radio
`R = 6378137 m`, no como el elipsoide WGS84.

## Fórmulas

Dado un punto en grados decimales `(lon, lat)`:

```
x = lon * 20037508.34 / 180
y = ln(tan((90 + lat) * pi / 360)) * 20037508.34 / 180
```

Resultado: `(x, y)` en metros, con origen en el centro del mapa (0,0)
correspondiente a `(0°, 0°)`.

El factor `20037508.34 = pi * 6378137` es la mitad de la circunferencia
terrestre en metros.

## Clamping de latitud

La proyección diverge en los polos. Para latitudes fuera del rango
`±85.05112878°` se satura el valor (clamp). Ese umbral corresponde al
cuadrado donde `y = ±20037508.34` (la mitad de la circunferencia polar
proyectada, donde el mapa es "cuadrado").

Convención del script `make_a_map.py`:

```python
WEB_MERCATOR_LAT_LIMIT = 85.05112878
lat = max(min(lat,  WEB_MERCATOR_LAT_LIMIT), -WEB_MERCATOR_LAT_LIMIT)
```

## Ajuste al lienzo

Para encajar un `bounding_box` (en metros) en un lienzo SVG `(W, H)` con
_padding_ `p`, manteniendo proporciones (sin distorsión):

```
availW = W - 2p
availH = H - 2p
scale  = min(availW / geoW, availH / geoH)   # uniform scale
```

Cualquier punto `(x, y)` del mapa se transforma a `(px, py)` del lienzo:

```
px = (x - min_x) * scale + p
py = (max_y - y) * scale + p    # y invertido (SVG origen arriba-izquierda)
```

`min` (no `max`) garantiza que el lado más grande del bbox encaje; el lado
más pequeño queda centrado con margen. Esto es lo correcto cuando el bbox
no es cuadrado en metros (típico para regiones administrativas alargadas).

## Limitaciones

| Propiedad | Web Mercator |
|-----------|--------------|
| Conforme (preserva ángulos locales) | Sí |
| Equiárea (preserva superficies) | No — distorsión crece con `|lat|` |
| Apta para navegación / calles | Sí |
| Apta para comparar áreas | No — usar Equal Earth o Albers |
| Apta para regiones polares | No — clamp a ±85° |

Para el caso de uso de la skill (calles, límites administrativos de
departamentos/municipios colombianos, parques urbanos), Web Mercator es
adecuado: las latitudes tropicales implican distorsión de área < 5%.

## Verificación numérica

Test incluido en `make_a_map.py --self-test`:

```python
x, y = project_web_mercator(0, 0)        # -> (0, 0)
x, y = project_web_mercator(180, 0)      # -> (20037508.34, 0)
x, y = project_web_mercator(0, 85.0511)  # -> (0, ~20037508.34)
```

## Referencias

- [EPSG:3857 — WGS84 / Pseudo-Mercator](https://epsg.io/3857)
- [OpenStreetMap — Slippy map tilenames](https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames)
- [Mapbox — Web Mercator](https://docs.mapbox.com/help/glossary/mercator/)