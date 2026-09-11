"""Tests de sync_calificaciones_clickup — status semántico → real.

La lista real de ClickUp puede no tener 'calificado'/'pendiente' (solo
'to do'/'complete'). El resolver debe mapear el semántico al nombre real
(literal → análogos → type) y nunca abortar.
"""
import sys
import types

# `client` (use-clickup) importa `dotenv`, que no está en el venv de tests.
# Lo stubeamos para poder importar sync_calificaciones_clickup sin dotenv.
_client_stub = types.ModuleType("client")
_client_stub.get_client = lambda: None  # noqa: E731
sys.modules.setdefault("client", _client_stub)

import sync_calificaciones_clickup as sync  # noqa: E402


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, statuses, task_status="to do"):
        self._statuses = statuses
        self._task_status = task_status

    def get(self, url):
        if url.startswith("/space/"):
            return _Resp({"statuses": self._statuses})
        if url.startswith("/task/"):
            return _Resp({"status": {"status": self._task_status}})
        return _Resp({})


def test_resolver_status_semantico_mapes_a_complete():
    """Sin 'calificado' literal, resuelve al status cerrado ('complete')."""
    c = _FakeClient([
        {"status": "to do", "type": "open"},
        {"status": "complete", "type": "closed"},
    ])
    assert sync.resolver_status_semantico(c, "s1", "calificado") == "complete"
    assert sync.resolver_status_semantico(c, "s1", "pendiente") == "to do"


def test_resolver_status_semantico_literal_existente():
    """Si 'calificado' existe literal, lo usa tal cual."""
    c = _FakeClient([{"status": "calificado", "type": "custom"}])
    assert sync.resolver_status_semantico(c, "s1", "calificado") == "calificado"


def test_resolver_status_semantico_fallback_por_tipo():
    """Sin análogos literales pero con status cerrado, cae por type."""
    c = _FakeClient([{"status": "Aprobado", "type": "closed"}])
    assert sync.resolver_status_semantico(c, "s1", "calificado") == "Aprobado"


def test_resolver_status_semantico_none_si_no_hay():
    """Sin status compatible devuelve None (no aborta)."""
    c = _FakeClient([{"status": "in review", "type": "custom"}])
    assert sync.resolver_status_semantico(c, "s1", "calificado") is None


def test_tarea_ya_calificada_con_status_real():
    """Reconoce una tarea ya 'complete' (no asume literal 'calificado')."""
    c = _FakeClient([{"status": "complete", "type": "closed"}], task_status="complete")
    assert sync.tarea_ya_calificada(c, "t1", "complete") is True
    assert sync.tarea_ya_calificada(c, "t1") is True  # por literales de hecho


def test_tarea_ya_calificada_no_matchea_to_do():
    c = _FakeClient([{"status": "to do", "type": "open"}], task_status="to do")
    assert sync.tarea_ya_calificada(c, "t1", "complete") is False
    assert sync.tarea_ya_calificada(c, "t1") is False
