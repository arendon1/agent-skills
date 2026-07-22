# SPEC: Geo-Information & SVG Mapping Skill

## 1. Overall objective

Design and implement a skill for the agent that lets it interact with
geographic APIs to obtain coordinates, administrative boundaries, and
street vectors, process that information, and export accurate vector
maps in SVG format.

## 2. Integration architecture (fallback strategy)

The skill implements a two-layer sequential query flow to guarantee data
availability and quality:

- **Primary provider (Layer 1): OpenStreetMap (OSM)**
  - **Geocoding:** Nominatim API.
  - **Geometries/vectors:** Overpass API (Overpass QL queries).
  - **Success criterion:** if the result is successful, contains valid
    geometric data, and has an acceptable confidence score, it is
    processed.
- **Backup provider (Layer 2): Mapbox**
  - **Activation:** invoked only if OSM fails (timeout, network
    error), exceeds its request rate limits, or returns an empty /
    insufficient dataset for the requested area.
  - **Service:** Mapbox Geocoding API.

## 3. Technical workflow

1. **Input:** receives the text or query with the desired location.
2. **Primary query (OSM):** the skill tries to extract geographic data
   from OpenStreetMap.
   - _If successful:_ sends the GeoJSON directly to the processing
     pipeline.
   - _If it fails or returns empty:_ the fallback to the Mapbox API is
     activated immediately.
3. **Cartographic projection:** transforms the spherical coordinates
   of the obtained GeoJSON into Cartesian coordinates (X, Y) using
   Web Mercator.
4. **Rendering:** translates the projected data into organized vector
   labels and generates the final SVG file.

### Step 1: Geocoding and data extraction

- **Input:** a string with the location (e.g. "Floridablanca,
  Santander") or explicit coordinates.
- **Expected output:** a structured object in **GeoJSON** format
  containing nodes (points of interest), _ways_ (streets, roads), and
  relations (polygon boundaries).

### Step 2: Normalization and cartographic projection

The agent must take the spherical geographic coordinates
`[Longitude, Latitude]` from the GeoJSON and project them onto a
two-dimensional Cartesian plane `(X, Y)` using the **Web Mercator
projection (EPSG:3857)** adapted to the required SVG canvas size.

- It must automatically compute the _Bounding Box_ to center and
  scale the content optimally within the canvas.

### Step 3: Vector SVG rendering (CORE structure requirement)

The skill must map geographic entities to valid SVG tags. It is a
**strictly mandatory requirement** that all elements be organized
into perfectly named and identified groups (`<g>`). This guarantees
direct human comprehension and allows the SVG to be imported and
edited as a clean design resource in tools like **Affinity Designer**
or **Microsoft PowerPoint**.

- **Organization by semantic layers:** each data category must be
  grouped inside a `<g>` tag with a semantic, clear, readable `id`
  attribute (e.g. `<g id="limites-administrativos">`,
  `<g id="calles-principales">`, `<g id="parques-y-zonas-verdes">`,
  `<g id="cuerpos-de-agua">`).
- **Line elements:** `LineString` and `MultiLineString` (streets,
  rivers) -> `<path d="..." />` elements with configurable style
  attributes (`stroke`, `stroke-width`).
- **Polygon elements:** `Polygon` and `MultiPolygon` (buildings,
  parks, urban zones) -> `<path d="..." />` elements with `fill` and
  `opacity` attributes.
- **Point elements:** `Point` (markers or key places) -> `<circle
  cx="..." cy="..." />` elements.

## 4. Script/function output requirements

Every execution of this skill must return a JSON object with the
following structure:

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

## 5. Acceptance criteria for the agent

- **Fallback validation:** if a connection error with
  Nominatim/Overpass is simulated, the skill must automatically
  switch to Mapbox without throwing critical stop exceptions.
- **Geometric precision:** the spatial proportions of the map in the
  resulting SVG must stay faithful to geographic reality, avoiding
  severe visual distortions (vertical/horizontal stretching).
- **Clean editable SVG code:** the generated SVG string must be
  well-indented, include a dynamic `viewBox` tag, not contain
  orphan elements, and — above all — exhibit a layer hierarchy
  (`id` in `<g>` tags) that is completely intuitive so a human can
  ungroup and change colors of streets or zones independently in
  their design software.

## 6. Harness constraints

- Skill agnostic (§9): no references to specific harnesses or tools
  in the SKILL.md body.
- Skill language: `es-CO` (the original spec is in es-CO).
- Layer: `domain`. Invocation: `auto`. `provides`: declared
  capabilities.
- Size: `SKILL.md <= 500` lines.
