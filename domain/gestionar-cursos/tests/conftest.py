"""conftest: pre-pobla sys.path y mockea console de Rich para tests en CI sin TTY."""
import os
import sys
from unittest.mock import MagicMock

import pytest

# Pre-poblar sys.path para que `import cli_calificaciones`,
# `import cli_clickup`, `import _parsing` funcionen desde cualquier cwd.
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

# Forzar importacion de los modulos aqui, una sola vez, para que
# `sys.modules` los contenga cuando el fixture autouse corra.
import _parsing  # noqa: F401


@pytest.fixture(autouse=True)
def mock_rich_console(monkeypatch):
    """Mockear console de Rich para que los tests no fallen en CI sin TTY.

    Importante: los modulos bajo test deben estar en sys.modules para que
    podamos parcharlos. Los tests hacen import local; usamos importlib para
    garantizar que existan.
    """
    import importlib

    for mod_name in ("cli_calificaciones", "cli_clickup"):
        if mod_name not in sys.modules:
            try:
                importlib.import_module(mod_name)
            except Exception:
                # cli_calificaciones importa navegador_cdp (selenium), que
                # puede no estar; los tests que no lo requieren lo manejan.
                pass

    fake_console = MagicMock()
    fake_console.print = MagicMock()
    fake_console.log = MagicMock()
    for mod_name in ("cli_calificaciones", "cli_clickup", "_parsing"):
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "console"):
            monkeypatch.setattr(mod, "console", fake_console)
    yield fake_console
