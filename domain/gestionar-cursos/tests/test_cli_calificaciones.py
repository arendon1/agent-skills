"""Tests de cli_calificaciones.

Cubre B1 (todos Pendiente no debe crashear) y B2 (persistencia antes
del resumen, resumen envuelto en try/except).
"""
import json
import os
import sys
import tempfile
from unittest.mock import patch

import pytest


def _make_item_pga(nombre, **overrides):
    """Helper: item minimo que sale del gradebook para tests."""
    base = {
        "row_id": f"row_{nombre}",
        "nombre": nombre,
        "tipo": "Quiz",
        "url": f"https://moodle/mod/quiz/view.php?id={abs(hash(nombre)) % 10000}",
        "mod_id": str(abs(hash(nombre)) % 10000),
        "ponderacion_pct": "10,00 %",
        "calificacion": "",  # Pendiente
        "rango": "0\u20135",
        "porcentaje": "",
        "aporte_curso": "",  # <- era "-" en el bug
        "estado": "Pendiente",
        "feedback": "",
    }
    base.update(overrides)
    return base


def test_imprimir_resumen_no_crashea_con_todos_pendiente(mock_rich_console):
    """B1: _imprimir_resumen con todos los items en Pendiente no debe lanzar.

    Antes: `float(it['aporte_curso'].replace(...).strip() or 0)` lanzaba
    ValueError cuando aporte_curso era "-".
    Despues: usa _parse_porcentaje que tolera centinelas.
    """
    import cli_calificaciones

    items = [
        _make_item_pga("Quiz 1", aporte_curso="-"),
        _make_item_pga("Quiz 2", aporte_curso="Sin calificar"),
        _make_item_pga("Tarea 1", aporte_curso=""),
        _make_item_pga("Foro 1", aporte_curso="N/A"),
    ]
    # Debe terminar sin excepcion.
    cli_calificaciones._imprimir_resumen(items)
    # La consola mockeada recibio al menos 2 prints (tabla + panel resumen).
    assert mock_rich_console.print.call_count >= 2


def test_imprimir_resumen_mezcla_calificados_y_pendientes(mock_rich_console):
    """Una mezcla realista: algunos calificados con aporte numerico, otros no."""
    import cli_calificaciones

    items = [
        _make_item_pga("Parcial 1", calificacion="4,80", estado="Aprobado", aporte_curso="24,00 %"),
        _make_item_pga("Quiz 1", aporte_curso="-", estado="Pendiente"),
        _make_item_pga("Tarea 1", calificacion="3,20", estado="Reprobado", aporte_curso="6,40 %"),
    ]
    cli_calificaciones._imprimir_resumen(items)
    assert mock_rich_console.print.call_count >= 2


def test_actualizar_md_actividad_escribe_seccion(mock_rich_console, tmp_path):
    """_actualizar_md_actividad agrega seccion ## Calificacion al .md."""
    import cli_calificaciones

    md_path = tmp_path / "actividad.md"
    md_path.write_text(
        "# Actividad 1\n\nDescripcion de la actividad.\n",
        encoding="utf-8",
    )
    item = _make_item_pga("Parcial 1", calificacion="4,80", estado="Aprobado", aporte_curso="24,00 %")
    cli_calificaciones._actualizar_md_actividad(str(md_path), item, "12345")

    contenido = md_path.read_text(encoding="utf-8")
    # La seccion incluye tilde en 'Calificacion' segun convencion del skill.
    assert "## Calificación" in contenido
    assert "4,80" in contenido
    assert "Aprobado" in contenido


def test_actualizar_md_actividad_reemplaza_seccion_existente(mock_rich_console, tmp_path):
    """Re-correr actualiza la seccion, no la duplica."""
    import cli_calificaciones

    md_path = tmp_path / "actividad.md"
    md_path.write_text(
        "# Actividad 1\n\n"
        "## Calificación\n\n"
        "| Campo | Valor |\n|---|---|\n"
        "| Nota | 2,00 |\n"
        "| Estado | Reprobado |\n\n"
        "_Viejo footer_\n",
        encoding="utf-8",
    )
    item = _make_item_pga("Parcial 1", calificacion="4,80", estado="Aprobado", aporte_curso="24,00 %")
    cli_calificaciones._actualizar_md_actividad(str(md_path), item, "12345")

    contenido = md_path.read_text(encoding="utf-8")
    # Solo una seccion Calificacion (con tilde)
    assert contenido.count("## Calificación") == 1
    # La nueva nota sobreescribio la vieja
    assert "4,80" in contenido
    assert "2,00" not in contenido
    assert "_Viejo footer_" not in contenido  # el footer viejo se reemplazo


def test_actualizar_snapshot_escribe_calificaciones(mock_rich_console, tmp_path):
    """_actualizar_snapshot agrega campo calificacion por actividad."""
    import cli_calificaciones

    cache = tmp_path / "_cache"
    cache.mkdir()
    snap_path = cache / "snapshot.json"
    snap_path.write_text(
        json.dumps(
            {
                "actividades": {
                    "Quiz 1 (https://moodle/mod/quiz/view.php?id=9999)": {
                        "nombre": "Quiz 1",
                        "fecha_apertura": "2026-07-01",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    item = _make_item_pga("Quiz 1", mod_id="9999", calificacion="4,50", estado="Aprobado")
    cli_calificaciones._actualizar_snapshot(str(snap_path), [item])

    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    key = next(iter(snap["actividades"]))
    assert "calificacion" in snap["actividades"][key]
    assert snap["actividades"][key]["calificacion"]["nota"] == "4,50"
    assert "calificaciones_capturadas" in snap


def test_orden_persistencia_antes_de_resumen_b2(mock_rich_console, tmp_path, monkeypatch):
    """B2: en main(), la persistencia (.md + snapshot) corre ANTES de
    _imprimir_resumen, incluso si _imprimir_resumen crashea.

    Verifica con un curso fake + snapshot.json fake, mockeando
    navegador_cdp para que no requiera Chrome.
    """
    import cli_calificaciones

    # Construir curso fake
    curso_dir = tmp_path / "2607B04G1-fake"
    curso_dir.mkdir()
    unidad = curso_dir / "Unidad-1" / "actividades"
    unidad.mkdir(parents=True)
    # El archivo .md debe matchear el item por nombre exacto (la normalizacion
    # del codigo no colapsa espacios en matching exacto, solo en tokens).
    (unidad / "Quiz 1.md").write_text("# Quiz 1\n", encoding="utf-8")
    cache = curso_dir / "_cache"
    cache.mkdir()
    snap_path = cache / "snapshot.json"
    snap_path.write_text(
        json.dumps(
            {
                "actividades": {
                    "Quiz 1 (https://moodle/mod/quiz/view.php?id=1111)": {
                        "nombre": "Quiz 1",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (curso_dir / "AGENTS.md").write_text(
        "[URL](https://moodle/course/view.php?id=7777)\n",
        encoding="utf-8",
    )

    # HTML minimo que produce 1 item Pendiente con aporte_curso="-"
    items_fake = [_make_item_pga("Quiz 1", mod_id="1111", aporte_curso="-")]

    # Mockear todos los pasos de navegador
    monkeypatch.setattr(cli_calificaciones, "_abrir_driver_cdp", lambda: object())
    monkeypatch.setattr(cli_calificaciones, "_verificar_sesion", lambda d: True)
    monkeypatch.setattr(cli_calificaciones, "_descargar_gradebook", lambda d, c: "<html></html>")
    monkeypatch.setattr(cli_calificaciones, "_parsear_gradebook", lambda html: items_fake)

    # Marcar el orden de las llamadas
    call_log = []

    real_actualizar_md = cli_calificaciones._actualizar_md_actividad
    real_actualizar_snap = cli_calificaciones._actualizar_snapshot
    real_imprimir = cli_calificaciones._imprimir_resumen

    def tracking_md(path, item, courseid):
        call_log.append(("md", item["nombre"]))
        return real_actualizar_md(path, item, courseid)

    def tracking_snap(path, items):
        call_log.append(("snap", len(items)))
        return real_actualizar_snap(path, items)

    def crashing_imprimir(items):
        call_log.append(("resumen_start",))
        # Crash controlado: simula que el render del table revienta
        raise RuntimeError("resumen explota")
        # unreachable, pero queremos ver que la persistencia ya corrio
        call_log.append(("resumen_end",))

    monkeypatch.setattr(cli_calificaciones, "_actualizar_md_actividad", tracking_md)
    monkeypatch.setattr(cli_calificaciones, "_actualizar_snapshot", tracking_snap)
    monkeypatch.setattr(cli_calificaciones, "_imprimir_resumen", crashing_imprimir)

    # Invocar main() sin dry-run. main() parsea argv -> hay que mockear sys.argv
    monkeypatch.setattr(sys, "argv", ["cli_calificaciones.py", str(curso_dir)])
    cli_calificaciones.main()

    # La persistencia (md + snap) ocurrio ANTES del intento de resumen.
    tipos = [t[0] for t in call_log]
    assert "md" in tipos
    assert "snap" in tipos
    assert "resumen_start" in tipos
    idx_md = tipos.index("md")
    idx_snap = tipos.index("snap")
    idx_resumen = tipos.index("resumen_start")
    assert idx_md < idx_resumen, "MD debe escribirse antes del resumen"
    assert idx_snap < idx_resumen, "Snapshot debe escribirse antes del resumen"

    # El md de la actividad quedo escrito
    md_contenido = (unidad / "Quiz 1.md").read_text(encoding="utf-8")
    assert "## Calificación" in md_contenido

    # El snapshot.json quedo actualizado
    snap = json.loads(snap_path.read_text(encoding="utf-8"))
    assert "calificaciones_capturadas" in snap
