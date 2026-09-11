"""La identidad de un endpoint CDP es el PERFIL, nunca el puerto.

Política (Andrés, 2026-09-11): solo dos perfiles Chrome autorizados para
agentes, y ambos viven en ~/.agents/. El puerto puede variar según
disponibilidad; el perfil no. Por eso el anclaje es perfil→puerto (por
descubrimiento), jamás puerto→perfil (hardcodeado).
"""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import navegador_cdp as nc  # noqa: E402


@pytest.fixture(autouse=True)
def _estado_limpio(monkeypatch):
    monkeypatch.setattr(nc, "_profile_dir", None)
    monkeypatch.setattr(nc, "_puerto_activo", None)
    monkeypatch.setattr(nc, "_driver", None)


# --- allowlist de perfiles ------------------------------------------------

def test_moodle_y_globant_estan_autorizados():
    assert nc.is_authorized("~/.agents/.browserdata")
    assert nc.is_authorized("~/.agents/.browserdata-globant")


def test_perfil_efimero_de_la_prueba_con_cmux_no_esta_autorizado():
    assert not nc.is_authorized("/tmp/cmux-chrome-movistar-1787969049")


def test_perfil_creado_por_cwd_no_esta_autorizado():
    assert not nc.is_authorized("~/.agents/skills/gestionar-cursos/scripts/.browserdata")


def test_set_profile_dir_rechaza_perfil_no_autorizado():
    with pytest.raises(ValueError):
        nc.set_profile_dir("/tmp/lo-que-sea")


def test_set_profile_dir_acepta_perfil_autorizado():
    nc.set_profile_dir("~/.agents/.browserdata")
    assert nc.get_profile_dir() == nc._normalize_profile("~/.agents/.browserdata")


# --- descubrimiento: el anclaje es el perfil ------------------------------

def test_extrae_user_data_dir_del_command_line():
    args = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--remote-debugging-port=9224",
        "--user-data-dir=/Users/x/.agents/.browserdata",
    ]
    assert nc._user_data_dir_de(args) == "/Users/x/.agents/.browserdata"
    assert nc._user_data_dir_de([]) is None
    assert nc._user_data_dir_de(None) is None


def test_descubre_por_perfil_aunque_el_puerto_no_sea_el_esperado(monkeypatch):
    # El perfil de Moodle vive en 9237, no en el "canónico" 9224.
    amarre = {
        9237: "~/.agents/.browserdata",
        9229: "/tmp/cmux-chrome-movistar-9999",
    }
    monkeypatch.setattr(nc, "perfil_de_puerto", lambda p: amarre.get(p))
    encontrados = nc.descubrir_perfiles(puertos=[9237, 9229])
    assert encontrados[nc._normalize_profile("~/.agents/.browserdata")] == 9237


def test_puerto_para_perfil_sigue_al_perfil_cuando_cambia_de_puerto(monkeypatch):
    amarre = {9231: "~/.agents/.browserdata"}
    monkeypatch.setattr(nc, "perfil_de_puerto", lambda p: amarre.get(p))
    assert nc.puerto_para_perfil("~/.agents/.browserdata") == 9231


def test_puerto_para_perfil_resuelve_igual_para_distintos_puertos(monkeypatch):
    for puerto in (9222, 9224, 9233):
        monkeypatch.setattr(
            nc, "perfil_de_puerto",
            lambda p, _puerto=puerto: "~/.agents/.browserdata" if p == _puerto else None,
        )
        assert nc.puerto_para_perfil("~/.agents/.browserdata") == puerto


def test_puerto_para_perfil_ignora_endpoints_no_autorizados(monkeypatch):
    # Lo único vivo en el rango es un Chrome efímero no autorizado:
    # no hay que devolver nada ni tocarlo.
    monkeypatch.setattr(
        nc, "perfil_de_puerto",
        lambda p: "/tmp/cmux-chrome-movistar-9999" if p == 9222 else None,
    )
    assert nc.puerto_para_perfil("~/.agents/.browserdata") is None


def test_puerto_libre_esquiva_los_ocupados(monkeypatch):
    ocupados = {9222, 9223, 9224}
    monkeypatch.setattr(nc, "_is_port_open", lambda host, p: p in ocupados)
    assert nc._puerto_libre() == 9225


# --- efímeros de prueba se reconocen y se nombran; no se persisten --------

def test_perfil_efimero_de_prueba_se_clasifica_como_efimero():
    assert nc.clasificar_perfil("/tmp/cmux-chrome-movistar-1787969049") == "efimero"


def test_perfiles_autorizados_se_clasifican_como_autorizados():
    assert nc.clasificar_perfil("~/.agents/.browserdata") == "autorizado"
    assert nc.clasificar_perfil("~/.agents/.browserdata-globant") == "autorizado"


def test_perfil_arbitrario_es_desconocido():
    assert nc.clasificar_perfil("/tmp/perfil-arbitrario") == "desconocido"


def test_inventario_nombra_cada_endpoint(monkeypatch):
    amarre = {
        9222: "/tmp/cmux-chrome-movistar-1",
        9231: "/tmp/perfil-arbitrario",
    }
    monkeypatch.setattr(nc, "perfil_de_puerto", lambda p: amarre.get(p))
    inv = nc.inventario_cdp(puertos=[9222, 9231, 9232])
    assert inv == [
        {"puerto": 9222,
         "perfil": nc._normalize_profile("/tmp/cmux-chrome-movistar-1"),
         "clase": "efimero"},
        {"puerto": 9231,
         "perfil": nc._normalize_profile("/tmp/perfil-arbitrario"),
         "clase": "desconocido"},
    ]


def test_perfil_efimero_no_captura_el_flujo_de_moodle(monkeypatch):
    """Un Chrome de prueba efímero en el rango no debe romper ni secuestrar
    Moodle: se ignora y el skill abre el suyo con el perfil autorizado."""
    monkeypatch.setattr(
        nc, "perfil_de_puerto",
        lambda p: "/tmp/cmux-chrome-movistar-1" if p == 9222 else None,
    )
    assert nc.puerto_para_perfil(nc.PROFILE_MOODLE) is None


def test_error_de_perfil_sugiere_la_ruta_correcta():
    with pytest.raises(ValueError) as exc:
        nc.set_profile_dir("~/.browserdata-globant")  # ruta legacy, ya movida
    assert "¿Querías decir ~/.agents/.browserdata-globant?" in str(exc.value)
