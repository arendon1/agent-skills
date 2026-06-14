# ADR 0001: H5P Offline Strategy — Proxy HTML, Not True Offline

## Status

Accepted

## Context

Moodle H5P interactive content is served server-side via `mod/hvp/embed.php?id=XXX`. The user asked whether a true offline copy is possible.

The options were:
- **Option A**: Create local proxy HTML that embeds H5P via iframe pointing to Moodle. Requires internet.
- **Option B**: Download `.h5p` package files directly. Requires Moodle admin/backend access — not available to students.
- **Option C**: Skip H5P entirely. Loses all interactive learning content.

## Decision

Use **Option A**: Proxy HTML files. Each H5P activity becomes a local `.html` file with an iframe loading `embed.php?id=XXX` from Moodle.

## Consequences

- **Positive**: No admin access required. Simple to implement. Content remains interactive.
- **Negative**: Requires internet connection to load. Not truly offline.
- **Mitigation**: Document clearly that H5P proxies need internet. Label them `[Interactivo — requiere internet]`.

## Notes

If Uniremington ever enables H5P export for students, we can revisit Option B. Until then, proxy HTML is the only viable approach.
