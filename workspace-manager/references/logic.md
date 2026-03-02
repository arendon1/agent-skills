# File Organization Logic

Standards for project directory structure and file naming to maintain codebase maintainability.

## 1. Directory Structure Principles

- **Separation of Concerns**: Group files by functional domain or layer (e.g., `client/`, `server/`, `shared/`).
- **Standardized Locations**:
  - `docs/`: Project documentation.
  - `tests/`: Unit and integration tests (mirroring source structure).
  - `scripts/`: Utility scripts and automation.
  - `.agent/`: Configuration and skills for AI agents.

## 2. Naming Conventions

- **Files**: Use `kebab-case` or `snake_case` consistently. Avoid spaces or special characters.
- **Directories**: Use `kebab-case`.
- **Extensions**: Always use standard extensions (`.js`, `.py`, `.md`).

## 3. Configuration Files

- Configuration should reside in the root directory (e.g., `package.json`, `requirements.txt`, `.env.example`).
- Secret keys must NEVER be committed; use `.gitignore` and `.env`.

## 4. Documentation

- Every major directory should contain a `README.md` explaining its purpose and contents.
- `CLAUDE.md` or `PROJECT.md` serves as the source of truth for high-level organization rules.
