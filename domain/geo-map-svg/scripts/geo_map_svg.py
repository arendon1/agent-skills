#!/usr/bin/env python3
"""geo-map-svg — geographic data -> clean editable SVG.

Two-tier provider chain:
  - Layer 1: OpenStreetMap (Nominatim for geocoding, Overpass for geometry)
  - Layer 2: Mapbox Geocoding (fallback only when Layer 1 fails or is empty)

Projection: Web Mercator (EPSG:3857) clipped to lat +/-85.05112878.

Output: indented SVG with semantic <g id="..."> layers, ready for editing
in any vector design tool.

Stdlib-only. No third-party dependencies.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USER_AGENT = "agent-skills/geo-map-svg/1.0"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
)
MAPBOX_GEOCODING = "https://api.mapbox.com/geocoding/v5/mapbox.places"
DEFAULT_TIMEOUT = 10
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
DEFAULT_PADDING = 24
WEB_MERCATOR_LAT_LIMIT = 85.05112878
MAPBOX_TOKEN_ENV = "MAPBOX_TOKEN"

# Semantic layer ids — these are the public contract for downstream editors.
LAYER_LIMITS = "limites-administrativos"
LAYER_WATER = "cuerpos-de-agua"
LAYER_PARKS = "parques-y-zonas-verdes"
LAYER_BUILDINGS = "edificios"
LAYER_STREETS = "calles-principales"
LAYER_POINTS = "puntos-de-interes"

LAYER_ORDER = (
    LAYER_LIMITS,
    LAYER_WATER,
    LAYER_PARKS,
    LAYER_BUILDINGS,
    LAYER_STREETS,
    LAYER_POINTS,
)

LAYER_STYLES: dict[str, dict[str, str]] = {
    LAYER_LIMITS:     {"stroke": "#5b3a29", "stroke-width": "1.8", "fill": "none"},
    LAYER_WATER:      {"stroke": "#3b6e8f", "stroke-width": "0.6", "fill": "#a7d0e6", "fill-opacity": "0.85"},
    LAYER_PARKS:      {"stroke": "#6f9659", "stroke-width": "0.6", "fill": "#bfe3a8", "fill-opacity": "0.7"},
    LAYER_BUILDINGS:  {"stroke": "#b8b3aa", "stroke-width": "0.3", "fill": "#e8e0d4", "fill-opacity": "0.55"},
    LAYER_STREETS:    {"stroke": "#c98a4b", "stroke-width": "1.2", "fill": "none"},
    LAYER_POINTS:     {"fill": "#c0392b", "stroke": "#7a1f17", "stroke-width": "0.5"},
}

# Background and title
BG_FILL = "#faf7f2"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class GeoFeature:
    """A single renderable geographic feature, classified into a layer."""

    layer: str
    geometry_type: str  # Point | LineString | Polygon | MultiLineString | MultiPolygon
    coordinates: Any    # (lon, lat) for Point; list-of-rings for polygons; flat list for lines


# ---------------------------------------------------------------------------
# Web Mercator projection (EPSG:4326 -> EPSG:3857)
# ---------------------------------------------------------------------------


def project_web_mercator(lon: float, lat: float) -> tuple[float, float]:
    """Project WGS84 lon/lat to Web Mercator meters.

    Lat is clamped to +/- 85.05112878 (Mercator singularity).
    Returns meters (x, y) on the Web Mercator plane.
    """
    lat = max(min(lat, WEB_MERCATOR_LAT_LIMIT), -WEB_MERCATOR_LAT_LIMIT)
    x = lon * 20037508.34 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * 20037508.34 / 180.0
    return x, y


def _walk_coords(coords: Any, fn: Callable[[float, float], None]) -> None:
    """Recursively apply fn(lon, lat) to every coordinate pair in any nesting depth."""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        fn(coords[0], coords[1])
    else:
        for c in coords:
            _walk_coords(c, fn)


def compute_bbox_meters(features: Iterable[GeoFeature]) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) in Web Mercator meters."""
    min_x = min_y = math.inf
    max_x = max_y = -math.inf

    def upd(lon: float, lat: float) -> None:
        nonlocal min_x, min_y, max_x, max_y
        x, y = project_web_mercator(lon, lat)
        if x < min_x: min_x = x
        if x > max_x: max_x = x
        if y < min_y: min_y = y
        if y > max_y: max_y = y

    for f in features:
        _walk_coords(f.coordinates, upd)

    if not math.isfinite(min_x):
        return (0.0, 0.0, 1.0, 1.0)
    return (min_x, min_y, max_x, max_y)


def make_transform(
    features: Iterable[GeoFeature],
    width: int,
    height: int,
    padding: int = DEFAULT_PADDING,
) -> tuple[Callable[[float, float], tuple[float, float]], tuple[float, float, float, float]]:
    """Return (transform_fn, raw_bbox_meters).

    transform_fn(lon, lat) -> (px, py) in canvas coordinates.
    Uniform scale = min(availW/geoW, availH/geoH) preserves aspect ratio.
    """
    feat_list = list(features)
    min_x, min_y, max_x, max_y = compute_bbox_meters(feat_list)
    geo_w = max_x - min_x
    geo_h = max_y - min_y
    avail_w = max(width - 2 * padding, 1)
    avail_h = max(height - 2 * padding, 1)
    if geo_w <= 0 or geo_h <= 0:
        # Degenerate bbox (e.g. single point) — center it
        cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
        def identity(lon: float, lat: float, _cx: float = cx, _cy: float = cy) -> tuple[float, float]:
            x, y = project_web_mercator(lon, lat)
            return (width / 2 + (x - _cx), height / 2 + (_cy - y))
        return identity, (min_x, min_y, max_x, max_y)
    scale = min(avail_w / geo_w, avail_h / geo_h)

    def transform(lon: float, lat: float) -> tuple[float, float]:
        x, y = project_web_mercator(lon, lat)
        px = (x - min_x) * scale + padding
        py = (max_y - y) * scale + padding  # SVG y-axis inverted
        return (px, py)

    return transform, (min_x, min_y, max_x, max_y)


# ---------------------------------------------------------------------------
# Provider 1: OSM (Nominatim + Overpass)
# ---------------------------------------------------------------------------


def _http_get_json(url: str, *, data: bytes | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict | list | None:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    req = Request(url, data=data, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
        print(f"[osm] http error for {url[:80]}: {e}", file=sys.stderr)
        return None


def nominatim_search(query: str) -> dict | None:
    params = urlencode({"q": query, "format": "json", "limit": 1, "polygon_geojson": 1})
    url = f"{NOMINATIM_URL}?{params}"
    data = _http_get_json(url)
    if isinstance(data, list) and data:
        return data[0]
    return None


def _bbox_from_nominatim(result: dict) -> tuple[float, float, float, float]:
    """Nominatim returns boundingbox as [minlat, maxlat, minlon, maxlon] (strings).
    Convert to (min_lon, min_lat, max_lon, max_lat)."""
    bb = result.get("boundingbox", [])
    if len(bb) != 4:
        return (0.0, 0.0, 0.0, 0.0)
    min_lat, max_lat, min_lon, max_lon = (float(x) for x in bb)
    return (min_lon, min_lat, max_lon, max_lat)


def overpass_query(bbox: tuple[float, float, float, float], *, timeout: int = 25) -> dict | None:
    min_lon, min_lat, max_lon, max_lat = bbox
    bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    ql = (
        "[out:json][timeout:" + str(timeout) + "];\n"
        "(\n"
        '  way["boundary"="administrative"](' + bbox_str + ');\n'
        '  way["highway"~"motorway|trunk|primary|secondary|tertiary"](' + bbox_str + ');\n'
        '  way["waterway"](' + bbox_str + ');\n'
        '  way["natural"="water"](' + bbox_str + ');\n'
        '  way["leisure"="park"](' + bbox_str + ');\n'
        '  way["landuse"="park"](' + bbox_str + ');\n'
        '  way["building"](' + bbox_str + ');\n'
        '  node["place"~"city|town|village|hamlet"](' + bbox_str + ');\n'
        ");\n"
        "out geom;\n"
    )
    for url in OVERPASS_URLS:
        data = _http_get_json(url, data=ql.encode("utf-8"), timeout=DEFAULT_TIMEOUT + timeout)
        if isinstance(data, dict) and data.get("elements"):
            return data
    return None


def _classify_way(tags: dict) -> str | None:
    if tags.get("boundary") == "administrative":
        return LAYER_LIMITS
    hw = tags.get("highway")
    if hw in ("motorway", "trunk", "primary", "secondary", "tertiary"):
        return LAYER_STREETS
    if tags.get("waterway") in ("river", "stream", "canal"):
        return LAYER_WATER
    if tags.get("natural") == "water":
        return LAYER_WATER
    if tags.get("water"):
        return LAYER_WATER
    if tags.get("leisure") == "park":
        return LAYER_PARKS
    if tags.get("landuse") == "park" or tags.get("landuse") == "forest":
        return LAYER_PARKS
    if tags.get("building"):
        return LAYER_BUILDINGS
    return None


def parse_overpass(data: dict) -> list[GeoFeature]:
    features: list[GeoFeature] = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        if el["type"] == "way":
            coords = [(float(n["lon"]), float(n["lat"])) for n in el.get("geometry", [])]
            if len(coords) < 2:
                continue
            layer = _classify_way(tags)
            if layer is None:
                continue
            if coords[0] == coords[-1]:
                features.append(GeoFeature(layer=layer, geometry_type="Polygon", coordinates=[coords]))
            elif layer in (LAYER_LIMITS, LAYER_BUILDINGS, LAYER_PARKS, LAYER_WATER):
                # closed-ish administrative/water/park polygons often self-close at midpoint
                features.append(GeoFeature(layer=layer, geometry_type="Polygon", coordinates=[coords]))
            else:
                features.append(GeoFeature(layer=layer, geometry_type="LineString", coordinates=coords))
        elif el["type"] == "relation":
            # Recurse into relation members (out geom on relations is heavy; skip for v1)
            continue
        elif el["type"] == "node":
            if "place" in tags or tags.get("name"):
                features.append(GeoFeature(
                    layer=LAYER_POINTS,
                    geometry_type="Point",
                    coordinates=(float(el["lon"]), float(el["lat"])),
                ))
    return features


# ---------------------------------------------------------------------------
# Provider 2: Mapbox (fallback)
# ---------------------------------------------------------------------------


def mapbox_search(query: str, token: str) -> dict | None:
    encoded = quote(query, safe="")
    params = urlencode({"access_token": token, "limit": 1, "types": "place,region,country,locality"})
    url = f"{MAPBOX_GEOCODING}/{encoded}.json?{params}"
    data = _http_get_json(url)
    if isinstance(data, dict):
        feats = data.get("features", [])
        return feats[0] if feats else None
    return None


# ---------------------------------------------------------------------------
# SVG rendering
# ---------------------------------------------------------------------------


def _ring_to_path_d(ring: list[tuple[float, float]], transform: Callable[[float, float], tuple[float, float]]) -> str:
    if not ring:
        return ""
    parts: list[str] = []
    for i, (lon, lat) in enumerate(ring):
        x, y = transform(lon, lat)
        cmd = "M" if i == 0 else "L"
        parts.append(f"{cmd}{x:.2f},{y:.2f}")
    parts.append("Z")
    return " ".join(parts)


def _line_to_path_d(line: list[tuple[float, float]], transform: Callable[[float, float], tuple[float, float]]) -> str:
    if not line:
        return ""
    parts = []
    for i, (lon, lat) in enumerate(line):
        x, y = transform(lon, lat)
        cmd = "M" if i == 0 else "L"
        parts.append(f"{cmd}{x:.2f},{y:.2f}")
    return " ".join(parts)


def _polygon_to_path_d(coords: Any, transform: Callable[[float, float], tuple[float, float]]) -> str:
    """coords: list of rings (each ring = list of [lon, lat])."""
    if not coords:
        return ""
    # If single ring passed as flat list, wrap
    if coords and isinstance(coords[0][0], (int, float)):
        rings = [coords]
    else:
        rings = coords
    return " ".join(_ring_to_path_d(r, transform) for r in rings if r)


def _style_attrs(style: dict[str, str]) -> str:
    return " ".join(f'{k}="{v}"' for k, v in style.items())


def render_svg(
    features: list[GeoFeature],
    width: int,
    height: int,
    title: str = "Mapa",
) -> str:
    transform, _ = make_transform(features, width, height)
    by_layer: dict[str, list[GeoFeature]] = {}
    for f in features:
        by_layer.setdefault(f.layer, []).append(f)

    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    lines.append(f'  <title>{title}</title>')
    lines.append(f'  <rect x="0" y="0" width="{width}" height="{height}" fill="{BG_FILL}"/>')

    for layer in LAYER_ORDER:
        items = by_layer.get(layer)
        if not items:
            continue
        style = LAYER_STYLES.get(layer, {})
        attrs = _style_attrs(style)
        lines.append(f'  <g id="{layer}" {attrs}>')
        for f in items:
            if f.geometry_type == "Point":
                x, y = transform(*f.coordinates)
                r = "4"
                lines.append(f'    <circle cx="{x:.2f}" cy="{y:.2f}" r="{r}"/>')
            elif f.geometry_type in ("LineString", "MultiLineString"):
                lines.append(f'    <path d="{_line_to_path_d(f.coordinates, transform)}"/>')
            elif f.geometry_type in ("Polygon", "MultiPolygon"):
                lines.append(f'    <path d="{_polygon_to_path_d(f.coordinates, transform)}"/>')
        lines.append("  </g>")

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


_COORD_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def _is_explicit_coords(query: str) -> tuple[bool, float, float] | None:
    m = _COORD_RE.match(query)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return True, lat, lon


def _expand_bbox(bbox: tuple[float, float, float, float], factor: float = 0.15) -> tuple[float, float, float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    pad_lon = (max_lon - min_lon) * factor
    pad_lat = (max_lat - min_lat) * factor
    return (min_lon - pad_lon, min_lat - pad_lat, max_lon + pad_lon, max_lat + pad_lat)


def _bbox_for_point(lat: float, lon: float, deg: float = 0.04) -> tuple[float, float, float, float]:
    return (lon - deg, lat - deg, lon + deg, lat + deg)


def generate_map(
    query: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    mapbox_token: str | None = None,
) -> dict:
    """Main entry point. Returns dict matching the SKILL.md output schema."""
    token = mapbox_token or os.environ.get(MAPBOX_TOKEN_ENV)
    provider_used: str = "none"
    center: list[float] | None = None
    bbox: tuple[float, float, float, float] | None = None
    features: list[GeoFeature] = []

    # --- Layer 1: OSM ---------------------------------------------------
    explicit = _is_explicit_coords(query)
    if explicit:
        _, lat, lon = explicit
        center = [lat, lon]
        bbox = _bbox_for_point(lat, lon)
        provider_used = "osm"
        data = overpass_query(_expand_bbox(bbox, factor=0.4))
        if data:
            features = parse_overpass(data)
    else:
        nomi = nominatim_search(query)
        if nomi:
            lat = float(nomi["lat"])
            lon = float(nomi["lon"])
            center = [lat, lon]
            bbox = _bbox_from_nominatim(nomi)
            provider_used = "osm"
            data = overpass_query(_expand_bbox(bbox))
            if data:
                features = parse_overpass(data)

    # --- Layer 2: Mapbox fallback --------------------------------------
    if not features and token:
        mb = mapbox_search(query, token)
        if mb:
            lon, lat = mb["center"]
            center = [lat, lon]
            bbox = _bbox_for_point(lat, lon, deg=0.05)
            provider_used = "mapbox"
            # Mapbox Geocoding doesn't return Overpass-equivalent geometry.
            # Emit a single marker at the resolved coordinate.
            features = [GeoFeature(
                layer=LAYER_POINTS,
                geometry_type="Point",
                coordinates=(float(lon), float(lat)),
            )]

    if not features:
        return {
            "status": "error",
            "error": "no geometry returned by OSM and no Mapbox fallback available",
            "provider_used": provider_used,
        }

    svg = render_svg(features, width, height, title=f"Mapa: {query}")
    return {
        "status": "success",
        "provider_used": provider_used,
        "metadata": {
            "center_coords": center,
            "bounding_box": list(bbox) if bbox else None,
            "dimensions": {"width": width, "height": height},
        },
        "svg_raw": svg,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_result(result: dict, out_path: str | None) -> None:
    if out_path and result.get("status") == "success":
        Path(out_path).write_text(result["svg_raw"], encoding="utf-8")
        result["svg_path"] = str(Path(out_path).resolve())
    printable = {k: v for k, v in result.items() if k != "svg_raw"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    if result.get("status") == "success":
        svg_len = len(result.get("svg_raw", ""))
        msg = f"svg_raw: {svg_len} chars"
        if out_path:
            msg += f" -> {result['svg_path']}"
        print(msg, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(
        prog="geo_map_svg",
        description="Generate an editable SVG map from a geographic query (OSM + Mapbox fallback).",
    )
    p.add_argument("query", nargs="?", default=None,
                   help="Place name (e.g. 'Floridablanca, Santander') or 'lat,lon'. "
                        "Required unless --self-test.")
    p.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    p.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    p.add_argument("--mapbox-token", help="Mapbox access token (overrides $MAPBOX_TOKEN)")
    p.add_argument("--out", help="Write the SVG string to this file path")
    p.add_argument("--self-test", action="store_true", help="Run offline smoke checks and exit")
    args = p.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.query:
        p.error("query is required unless --self-test is set")

    result = generate_map(
        query=args.query,
        width=args.width,
        height=args.height,
        mapbox_token=args.mapbox_token,
    )
    _print_result(result, args.out)
    return 0 if result.get("status") == "success" else 1


# ---------------------------------------------------------------------------
# Offline self-test
# ---------------------------------------------------------------------------


def _self_test() -> int:
    """Offline checks: projection math, transform, SVG generation with mock data."""
    print("geo-map-svg self-test (offline, no network)")

    # 1. Web Mercator identity at equator
    x, y = project_web_mercator(0.0, 0.0)
    assert abs(x) < 1e-6 and abs(y) < 1e-6, f"equator origin failed: {x},{y}"

    # 2. Symmetry
    x_e, y_e = project_web_mercator(10.0, 20.0)
    x_w, y_w = project_web_mercator(-10.0, 20.0)
    assert abs(x_e + x_w) < 1e-6, f"lon symmetry failed: {x_e} vs {x_w}"
    assert abs(y_e - y_w) < 1e-6, f"lat y should be symmetric: {y_e} vs {y_w}"

    # 3. Lat clamping
    _, y_clamped = project_web_mercator(0.0, 89.5)
    _, y_max = project_web_mercator(0.0, WEB_MERCATOR_LAT_LIMIT)
    assert y_clamped == y_max, "lat clamping at 89.5 should equal limit"

    # 4. Transform + SVG with mock features (Floridablanca-ish)
    mock = [
        GeoFeature(layer=LAYER_LIMITS, geometry_type="Polygon", coordinates=[
            [(-73.10, 7.05), (-73.05, 7.05), (-73.05, 7.08), (-73.10, 7.08), (-73.10, 7.05)],
        ]),
        GeoFeature(layer=LAYER_WATER, geometry_type="Polygon", coordinates=[
            [(-73.08, 7.06), (-73.07, 7.06), (-73.07, 7.07), (-73.08, 7.07), (-73.08, 7.06)],
        ]),
        GeoFeature(layer=LAYER_STREETS, geometry_type="LineString", coordinates=[
            (-73.10, 7.05), (-73.05, 7.07),
        ]),
        GeoFeature(layer=LAYER_POINTS, geometry_type="Point", coordinates=(-73.0856, 7.0625)),
    ]
    svg = render_svg(mock, 400, 300, title="self-test")
    # Acceptance: well-formed + semantic groups
    assert svg.startswith('<?xml'), "svg must start with xml declaration"
    assert 'viewBox="0 0 400 300"' in svg, "viewBox must match dimensions"
    for layer_id in LAYER_ORDER:
        if any(f.layer == layer_id for f in mock):
            assert f'<g id="{layer_id}"' in svg, f"missing semantic group for {layer_id}"
    assert svg.count("<g ") == sum(1 for f in mock if any(g.layer == f.layer for g in mock)), "extra groups"
    assert "<circle" in svg, "missing point circle"
    assert svg.rstrip().endswith("</svg>"), "svg must end with </svg>"

    # 5. Aspect ratio preservation (uniform scale)
    transform, raw = make_transform(mock, 400, 300, padding=24)
    px_top_left = transform(-73.10, 7.08)
    px_bot_right = transform(-73.05, 7.05)
    render_w = abs(px_bot_right[0] - px_top_left[0])
    render_h = abs(px_bot_right[1] - px_top_left[1])
    geo_w = abs(raw[2] - raw[0])
    geo_h = abs(raw[3] - raw[1])
    avail_w, avail_h = 400 - 2 * 24, 300 - 2 * 24
    expected_w = geo_w * min(avail_w / geo_w, avail_h / geo_h)
    expected_h = geo_h * min(avail_w / geo_w, avail_h / geo_h)
    assert abs(render_w - expected_w) < 1e-3, "render width doesn't match uniform-scale math"
    assert abs(render_h - expected_h) < 1e-3, "render height doesn't match uniform-scale math"

    print("PASS all offline checks (projection, transform, SVG structure, aspect ratio)")
    return 0


if __name__ == "__main__":
    sys.exit(main())