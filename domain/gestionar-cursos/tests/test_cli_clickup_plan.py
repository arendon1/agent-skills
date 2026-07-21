"""Tests de cli_clickup.py en modo plan-local.

Verifica:
- Produce sync_plan.json valido (schema completo con _meta, to_create,
  to_update, to_archive, unresolved).
- CERO requests HTTP. Verificable con unittest.mock.patch sobre
  requests.get/post/put (no se llaman).
- Idempotencia: to_update solo si hay calificacion.nota.
- Constraints: to_archive NUNCA to_delete.
"""
import json
import os
from unittest.mock import MagicMock, patch

import pytest


def _write(path, content):
    """Helper: escribe JSON o texto."""
    if isinstance(content, (dict, list)):
        content = json.dumps(content, indent=2, ensure_ascii=False)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _build_periodo_fake(tmp_path):
    """Crea un periodo academico fake con 1 curso + snapshot + calificaciones."""
    periodo = tmp_path / "2026-2-B1"
    curso = periodo / "2607B04G1-fake"
    (curso / "_cache").mkdir(parents=True)

    # clickup.json a nivel periodo
    _write(
        str(periodo / "clickup.json"),
        {
            "folder": {"id": "999", "name": "2026-2-B1"},
            "courses": {
                "CURSO_7777": {
                    "list_id": "123456",
                    "list_name": "FAKE COURSE",
                    "tasks": {
                        "parcial_1": {"id": "task_a1", "name": "Parcial 1"},
                        "quiz_1": {"id": "task_a2", "name": "Quiz 1"},
                    },
                }
            },
        },
    )

    # AGENTS.md con course ID 7777
    (curso / "AGENTS.md").write_text(
        "# Fake\n[URL](https://moodle/course/view.php?id=7777)\n**CODIGO**: 2607B04G1\n",
        encoding="utf-8",
    )

    # PGA.md con 2 actividades
    _write(
        str(curso / "PGA.md"),
        "| Semana | Unidad | Actividad | Valor | Fecha Inicio | Fecha Fin |\n"
        "|--|--|--|--|--|--|\n"
        "| 1 | 1 | Quiz 1 | 5% | (2026-07-01) | (2026-07-15) |\n"
        "| 2 | 1 | Parcial 1 | 25% | (2026-07-20) | (2026-08-05) |\n"
        "| 3 | 1 | Actividad Nueva | 10% | (2026-08-10) | (2026-08-20) |\n",
    )

    # snapshot.json con fechas reales
    _write(
        str(curso / "_cache" / "snapshot.json"),
        {
            "actividades": {
                "Quiz 1 (https://moodle/mod/quiz/view.php?id=11)": {
                    "nombre": "Quiz 1",
                    "fecha_apertura": "2026-07-02",
                    "fecha_cierre": "2026-07-16",
                },
                "Parcial 1 (https://moodle/mod/quiz/view.php?id=22)": {
                    "nombre": "Parcial 1",
                    "fecha_apertura": "2026-07-21",
                    "fecha_cierre": "2026-08-06",
                },
            }
        },
    )

    # calificaciones.json: solo Parcial 1 tiene nota
    _write(
        str(curso / "_cache" / "calificaciones_7777.json"),
        [
            {
                "nombre": "Parcial 1",
                "tipo": "Quiz",
                "calificacion": "4,80",
                "rango": "0\u20135",
                "porcentaje": "96,00 %",
                "aporte_curso": "24,00 %",
                "ponderacion_pct": "25,00 %",
                "estado": "Aprobado",
                "feedback": "Buen trabajo",
                "mod_id": "22",
            },
            {
                "nombre": "Quiz 1",
                "tipo": "Quiz",
                "calificacion": "",
                "rango": "0\u20135",
                "porcentaje": "",
                "aporte_curso": "-",
                "ponderacion_pct": "5,00 %",
                "estado": "Pendiente",
                "feedback": "",
                "mod_id": "11",
            },
        ],
    )

    return periodo


def test_sync_plan_produce_estructura_correcta(mock_rich_console, tmp_path):
    """sync_plan.json tiene _meta + 4 secciones (to_create, to_update, to_archive, unresolved)."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    rc = sync_clickup(str(periodo), dry_run=False)
    assert rc == 0

    plan_path = periodo / "sync_plan.json"
    assert plan_path.exists()

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert "_meta" in plan
    for k in ("to_create", "to_update", "to_archive", "unresolved"):
        assert k in plan, f"Falta seccion {k}"

    # _meta completo
    meta = plan["_meta"]
    assert meta["schema_version"] == 1
    assert meta["periodo"] == "2026-2"
    assert meta["bloque"] == "B1"
    assert "orchestration_hint" in meta
    assert meta["orchestration_hint"]["order"] == ["to_create", "to_update", "to_archive"]
    assert "use-clickup:create_task" in meta["orchestration_hint"]["tools_required"]
    assert "idempotency_keys" in meta


def test_sync_plan_to_create_incluye_actividad_nueva(mock_rich_console, tmp_path):
    """Actividad Nueva (no esta en tasks) va a to_create."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    sync_clickup(str(periodo), dry_run=False)

    plan = json.loads((periodo / "sync_plan.json").read_text(encoding="utf-8"))
    nombres_create = [c["name"] for c in plan["to_create"]]
    assert "Actividad Nueva" in nombres_create
    # Quiz 1 y Parcial 1 ya existen en tasks -> NO en to_create
    assert "Quiz 1" not in nombres_create
    assert "Parcial 1" not in nombres_create


def test_sync_plan_to_update_solo_con_calificacion(mock_rich_console, tmp_path):
    """to_update solo incluye actividades con calificacion.nota (idempotente)."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    sync_clickup(str(periodo), dry_run=False)

    plan = json.loads((periodo / "sync_plan.json").read_text(encoding="utf-8"))
    # Solo Parcial 1 tiene nota -> solo Parcial 1 en to_update
    assert len(plan["to_update"]) == 1
    upd = plan["to_update"][0]
    assert upd["task_id"] == "task_a1"
    assert upd["diff"]["status"]["to"] == "calificado"
    assert "comment" in upd
    assert upd["comment"]["text"].startswith("[calificaciones-auto]")
    assert "Calificacion" in upd["comment"]["text"]
    # status SIEMPRE por nombre, NUNCA status_id
    assert "status_id" not in upd["diff"]


def test_sync_plan_no_hace_requests_http(mock_rich_console, tmp_path):
    """V1 + B4: cli_clickup.py NO hace requests HTTP. Verificable con mock."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)

    with patch("requests.get") as mock_get, \
         patch("requests.post") as mock_post, \
         patch("requests.put") as mock_put, \
         patch("requests.delete") as mock_delete:
        rc = sync_clickup(str(periodo), dry_run=False)
        assert rc == 0
        # CERO requests HTTP
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        mock_put.assert_not_called()
        mock_delete.assert_not_called()  # to_archive NUNCA to_delete


def test_sync_plan_no_importa_use_clickup():
    """C1: cli_clickup.py no importa nada de use-clickup ni de requests."""
    import cli_clickup

    src = open(cli_clickup.__file__, encoding="utf-8").read()
    # No debe haber imports de use_clickup
    assert "import use_clickup" not in src
    assert "from use_clickup" not in src
    assert "import use-clickup" not in src
    # No debe haber requests.get / requests.post / requests.put / .delete
    assert "requests.get" not in src
    assert "requests.post" not in src
    assert "requests.put" not in src
    assert "requests.delete" not in src
    # No debe haber llamadas a la API HTTP de ClickUp
    assert "api.clickup.com" not in src


def test_sync_plan_unresolved_con_folder_null(mock_rich_console, tmp_path):
    """Si clickup.folder.id es null, el plan lo reporta en unresolved y no aborta."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    # Invalidar folder.id
    clickup = json.loads((periodo / "clickup.json").read_text(encoding="utf-8"))
    clickup["folder"]["id"] = None
    _write(str(periodo / "clickup.json"), clickup)

    rc = sync_clickup(str(periodo), dry_run=False)
    assert rc == 0

    plan = json.loads((periodo / "sync_plan.json").read_text(encoding="utf-8"))
    unresolved_items = [u["item"] for u in plan["unresolved"]]
    assert "folder" in unresolved_items


def test_sync_plan_unresolved_con_list_id_null(mock_rich_console, tmp_path):
    """Si el curso no tiene list_id, va a unresolved (el agente pausa)."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    clickup = json.loads((periodo / "clickup.json").read_text(encoding="utf-8"))
    clickup["courses"]["CURSO_7777"]["list_id"] = None
    _write(str(periodo / "clickup.json"), clickup)

    sync_clickup(str(periodo), dry_run=False)
    plan = json.loads((periodo / "sync_plan.json").read_text(encoding="utf-8"))
    unresolved_items = [u["item"] for u in plan["unresolved"]]
    assert "CURSO_7777" in unresolved_items


def test_sync_plan_dry_run_no_escribe_archivo(mock_rich_console, tmp_path):
    """Con --dry-run, sync_plan.json NO se escribe."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    rc = sync_clickup(str(periodo), dry_run=True)
    assert rc == 0
    assert not (periodo / "sync_plan.json").exists()


def test_sync_plan_to_create_tiene_due_date_ms(mock_rich_console, tmp_path):
    """due_date_ms en to_create es epoch ms desde la fecha de cierre del snapshot."""
    from cli_clickup import sync_clickup

    periodo = _build_periodo_fake(tmp_path)
    sync_clickup(str(periodo), dry_run=False)

    plan = json.loads((periodo / "sync_plan.json").read_text(encoding="utf-8"))
    nueva = next(c for c in plan["to_create"] if c["name"] == "Actividad Nueva")
    # snapshot no tiene Actividad Nueva -> cae al PGA
    assert nueva["due_date_source"] == "pga"
    # 2026-08-20 -> epoch ms
    assert nueva["due_date_ms"] is not None
    assert isinstance(nueva["due_date_ms"], int)
    assert nueva["due_date_ms"] > 0
