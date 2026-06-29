# PLAN: geo-map-svg skill

## §T.1 — Scaffold skill directory

- [x] Run `python3 utility/skill-forge/scripts/init.py geo-map-svg --path domain`.
- [x] Verify `domain/geo-map-svg/{SKILL.md,scripts,references,examples,evals}/` exists.

## §T.2 — Frontmatter (§F, §T, §L)

- [x] `name: geo-map-svg` (lowercase-hyphens).
- [x] `description` contains literal "Use when" / "Usa cuando".
- [x] `invocation: auto` (self-trigger on context).
- [x] `layer: domain` (geographic capability, like `make-a-diagram`).
- [x] `provides: [osm-nominatim, osm-overpass, mapbox-geocoding, web-mercator, svg-export]`.
- [x] `language: es-CO` (matches user's spec).
- [x] No harness/tool names in frontmatter or body (§A0).

## §T.3 — SKILL.md body

- [x] Principles (fallback-first, geometry-first, Web Mercator, JSON-stable, agnostic).
- [x] Preflight (Python >= 3.9, optional MAPBOX_TOKEN).
- [x] Workflow (input -> OSM -> fallback -> Mercator -> SVG).
- [x] Layer table with semantic `<g id>` ids.
- [x] CLI + module usage examples.
- [x] Output JSON schema (success + error).
- [x] Acceptance criteria table.
- [x] Internal structure diagram.
- [x] Operational notes (rate limits, languages).
- [x] Lines <= 500.

## §T.4 — Implementation `scripts/geo_map_svg.py`

- [x] Stdlib-only (no pip deps).
- [x] `project_web_mercator(lon, lat) -> (x, y)` with lat clamp.
- [x] `make_transform(features, W, H)` with uniform-scale aspect-ratio preservation.
- [x] `nominatim_search(query) -> dict | None`.
- [x] `overpass_query(bbox) -> dict | None` (tries 3 endpoints sequentially).
- [x] `parse_overpass(data) -> list[GeoFeature]` with `_classify_way(tags)`.
- [x] `mapbox_search(query, token) -> dict | None` (fallback).
- [x] `render_svg(features, W, H)` -> SVG string with semantic `<g id>` layers.
- [x] `generate_map(query, W, H, token) -> dict` orchestrator.
- [x] `--self-test` offline check (projection symmetry, clamp, SVG structure, aspect ratio).
- [x] Explicit lat,lon query parsing.
- [x] JSON output schema matches SPEC §4.
- [x] Error path returns `{status: error, ...}` instead of raising.

## §T.5 — References

- [x] `references/web-mercator.md` (math, clamping, fit-to-canvas, limitations).

## §T.6 — Examples

- [x] `examples/colombia-floridablanca.md` (run command, expected JSON, post-process).

## §T.7 — Eval

- [x] `evals/smoke.py` runs `--self-test` + `audit` (offline, no network).

## §T.8 — Audit + verify

- [x] `python3 utility/skill-forge/scripts/audit.py geo-map-svg` -> PASS (231 lines, well under 500).
- [x] `python3 domain/geo-map-svg/evals/smoke.py` -> PASS (self-test + audit).
- [x] Live SVG sanity check (mock features): viewBox dynamic, semantic `<g id>` groups, valid XML, indented.
- [x] Manifest regeneration: PASS (32 skills, domain=7 incl. geo-map-svg).
- [x] Forbidden-term scan (§A0): no harness/tool names in SKILL.md body.

## §T.9 — Optional commit (deferred until user asks)

- conventional: `feat(domain): add geo-map-svg skill for geographic SVG export`