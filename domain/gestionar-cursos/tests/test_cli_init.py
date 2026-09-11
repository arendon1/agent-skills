"""Tests de cli_init._escribir_cursos_json — auto-registro del perfil del curso.

Al inicializar/sincronizar un curso, cli_init debe cablearlo automáticamente al
orquestador escribiendo su perfil en cursos.json (raíz del período), para que los
workflows lo reciban vía args.cursos sin registro manual.
"""
import json
import os

import cli_init


def test_escribir_cursos_json_auto_registra(tmp_path):
    """cli_init crea el perfil en cursos.json con la info auto-capturada."""
    curso = tmp_path / "2608B04G9-mi-curso"
    curso.mkdir()
    (curso / "AGENTS.md").write_text(
        "**CODIGO**: 2608B04G9\n"
        "**MATERIA**: Mi Curso (Competencias)\n"
        "**CODIGO_MATERIA_REPORTE**: 1F0999\n"
        "**PROFESOR/TUTORA**: Juana Pérez (juan@uniremington.edu.co)\n",
        encoding="utf-8",
    )
    # clickup.json previo (como lo deja cli_init)
    json.dump(
        {
            "courses": {
                "2608B04G9-mi-curso": {
                    "list_id": "1000x0000009999",
                    "list_name": "Mi Curso - 2608B04G9",
                    "tasks": {},
                }
            }
        },
        open(os.path.join(tmp_path, "clickup.json"), "w", encoding="utf-8"),
    )
    datos = {
        "codigo": "2608B04G9",
        "nombre": "Mi Curso — Competencias comunicativas",
        "url": "https://aulavirtual.uniremington.edu.co/course/view.php?id=77777",
    }
    cli_init._escribir_cursos_json(
        str(tmp_path), str(curso), datos, datos["url"], periodo="2026-2", bloque="B1"
    )

    data = json.load(open(os.path.join(tmp_path, "cursos.json"), encoding="utf-8"))
    p = data["cursos"]["2608B04G9-mi-curso"]
    assert p["dir"] == str(curso)
    assert p["nombre"] == "Mi Curso — Competencias comunicativas"
    assert p["codigo"] == "2608B04G9"
    assert p["moodle_course_id"] == "77777"
    assert p["moodle_url"] == datos["url"]
    assert p["list_id_clickup"] == "1000x0000009999"
    assert p["profesor"] == "Juana Pérez"
    assert p["codigo_materia"] == "1F0999"
    assert p["periodo"] == "2026-2-B1"
    assert p["activo"] is True


def test_escribir_cursos_json_preserva_ediciones_manuales(tmp_path):
    """No pisa campos editados a mano (profesor, convenciones) si ya existen."""
    curso = tmp_path / "2608B04G8-otro-curso"
    curso.mkdir()
    (curso / "AGENTS.md").write_text("**CODIGO**: 2608B04G8\n", encoding="utf-8")
    ruta_cursos = os.path.join(tmp_path, "cursos.json")
    json.dump(
        {
            "cursos": {
                "2608B04G8-otro-curso": {
                    "profesor": "Profesor Editado",
                    "convenciones": {"rubrica_taller": "0/1/3/5"},
                    "tipo_materia": "tecnica",
                }
            }
        },
        open(ruta_cursos, "w", encoding="utf-8"),
    )
    datos = {
        "codigo": "2608B04G8",
        "nombre": "Otro Curso",
        "url": "https://x/course/view.php?id=88888",
    }
    cli_init._escribir_cursos_json(
        str(tmp_path), str(curso), datos, datos["url"], periodo="2026-2", bloque="B1"
    )

    data = json.load(open(ruta_cursos, encoding="utf-8"))
    p = data["cursos"]["2608B04G8-otro-curso"]
    assert p["profesor"] == "Profesor Editado"  # preservado
    assert p["convenciones"]["rubrica_taller"] == "0/1/3/5"  # preservado
    assert p["tipo_materia"] == "tecnica"  # preservado
    assert p["moodle_course_id"] == "88888"  # auto-completado
