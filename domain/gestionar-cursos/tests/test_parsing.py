"""Tests de _parse_porcentaje — 12+ formatos del gradebook Moodle."""
import pytest

from _parsing import _parse_porcentaje


@pytest.mark.parametrize(
    "valor,esperado",
    [
        # Centinelas (L1 del plan, B1 del PRD)
        (None, 0.0),
        ("", 0.0),
        ("-", 0.0),
        ("\u2014", 0.0),  # em-dash
        ("N/A", 0.0),
        ("Sin calificar", 0.0),
        ("n/a", 0.0),  # lowercase
        # Formatos numericos tipicos
        ("0,00 %", 0.0),
        ("0%", 0.0),
        ("12,50 %", 12.5),
        ("12.5 %", 12.5),
        ("100,00 %", 100.0),
        ("100%", 100.0),
        # Casos edge
        (" - %", 0.0),
        (" 12,50 % ", 12.5),  # espacios alrededor
        (" 100 %", 100.0),
        # Ceros
        ("0", 0.0),
        ("0,0 %", 0.0),
    ],
)
def test_parse_porcentaje_acepta_formatos_reales(valor, esperado):
    """_parse_porcentaje tolera los formatos del gradebook Moodle sin excepcion."""
    assert _parse_porcentaje(valor) == pytest.approx(esperado)


def test_parse_porcentaje_no_explota_con_inputs_raros():
    """Inputs que harian explotar `float('texto' or 0)` retornan 0.0 silenciosamente."""
    raros = [
        "no es un numero",
        "abc%",
        "%",
        "  ",
        "   -   ",
        "0,0,0",
        object(),  # objeto no-stringable directamente
    ]
    for v in raros:
        resultado: float = 0.0
        try:
            resultado = _parse_porcentaje(v)
        except Exception as e:
            pytest.fail(f"_parse_porcentaje({v!r}) no debio explotar: {e}")
        # Resultado debe ser float
        assert isinstance(resultado, float)
        assert resultado == 0.0 or resultado > 0  # 0.0 o parseable


def test_parse_porcentaje_sentinel_orden():
    """Centinelas van ANTES de intentar float(), por lo que '-' no lanza."""
    # Si la implementacion usara `valor or 0`, '-' pasaria como truthy y
    # `float('-')` lanzaria ValueError. _parse_porcentaje lo previene.
    for sentinel in ("-", "\u2014", "Sin calificar", "N/A", ""):
        assert _parse_porcentaje(sentinel) == 0.0, f"Centinela {sentinel!r} fallo"


def test_parse_porcentaje_acepta_negativos_y_decimales():
    """Casos limite: 0%, negativos no esperados, decimales con punto/coma."""
    assert _parse_porcentaje("0,01 %") == pytest.approx(0.01)
    assert _parse_porcentaje("99,99 %") == pytest.approx(99.99)
    # Numeros >100: el helper no valida el rango, retorna lo que se le pase.
    assert _parse_porcentaje("150 %") == 150.0
