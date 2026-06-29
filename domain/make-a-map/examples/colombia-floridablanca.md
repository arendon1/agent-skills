# Ejemplo: mapa de Floridablanca, Santander

## Caso de uso

Generar un mapa vectorial editable del municipio de Floridablanca (Colombia)
para insertar en una presentación académica sobre urbanismo del área
metropolitana de Bucaramanga.

## Ejecución

```bash
python3 domain/make-a-map/scripts/make_a_map.py \
    "Floridablanca, Santander, Colombia" \
    --width 1200 \
    --height 900 \
    --out docs/assets/floridablanca.svg
```

## Salida JSON

```json
{
  "status": "success",
  "provider_used": "osm",
  "metadata": {
    "center_coords": [7.0625, -73.0856],
    "bounding_box": [-73.13, 7.02, -73.04, 7.11],
    "dimensions": { "width": 1200, "height": 900 }
  },
  "svg_path": "/abs/path/docs/assets/floridablanca.svg"
}
```

## Resultado en editor

Al abrir `floridablanca.svg` en Affinity Designer / Illustrator / PowerPoint:

1. El SVG aparece agrupado en 6 capas semánticas: `limites-administrativos`,
   `cuerpos-de-agua`, `parques-y-zonas-verdes`, `edificios`,
   `calles-principales`, `puntos-de-interes`.
2. Cada `<g>` se puede colapsar/expandir individualmente.
3. Cambiar el `fill` del grupo `parques-y-zonas-verdes` afecta todos los
   polígonos de parques a la vez.
4. Mover o escalar el grupo `calles-principales` no desplaza el fondo
   ni los límites administrativos.

## Post-procesado típico

```python
# Cambiar paleta para impresión B/N
import re
svg = open("floridablanca.svg").read()
svg = svg.replace('fill="#a7d0e6"', 'fill="#cccccc"')      # agua
svg = svg.replace('fill="#bfe3a8"', 'fill="#dddddd"')      # parques
open("floridablanca-bn.svg", "w").write(svg)
```

## Notas

- Si el bounding box devuelto es muy ajustado, el render puede verse
  apretado. Probar `--width 1400 --height 1000`.
- Para mapas sin etiquetas de calles visibles (Overpass devuelve geometría
  sin `name`), añadir una capa `<g id="etiquetas">` con `<text>` desde un
  enriquecimiento adicional (futuro).