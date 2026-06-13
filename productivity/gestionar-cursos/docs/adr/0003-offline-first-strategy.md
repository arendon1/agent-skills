# ADR 0003: Offline-First Content Strategy

## Status

Accepted

## Context

The user wants all extractable content stored locally. This includes PDFs, images, and text content.

## Decision

**Offline-first for all extractable content.**

- PDFs → downloaded to `Unidad-X/materiales/`
- Images from `page` modules → downloaded to `Unidad-X/materiales/imagenes/`
- `page` text → converted to markdown with local image paths
- H5P → proxy HTML (requires internet, documented as exception)

## Consequences

- Larger disk footprint (~10-50 MB per course)
- No dependency on internet for reading course materials
- Image URLs in markdown rewritten to relative paths
- `pluginfile.php` URLs resolved to local files

## Exceptions

- H5P interactive content cannot be fully offline (see ADR-0001)
- Forum discussions are dynamic, only first post is extracted
