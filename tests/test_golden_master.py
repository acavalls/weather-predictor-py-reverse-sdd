"""Golden master del flujo central de negocio (/predict).

Compara la salida completa del caso de uso de predicción contra
tests/golden_master/master.json (ver LEEME junto al master).

REGLA: si este test falla, NO se regenera el master para "arreglarlo";
se investiga qué cambió y se documenta. La regeneración solo procede con
decisión de negocio documentada (constitución, Principio I/II).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_golden_master import MASTER, generar_master

MASTER_PATH = Path(MASTER)


@pytest.fixture(scope="module")
def master_guardado() -> dict:
    datos = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    # JSON serializa las claves int de los horizontes como texto; se
    # normalizan a int para comparar con la salida real del sistema.
    for caso in datos["casos"].values():
        caso["predictions"] = {int(h): v for h, v in caso["predictions"].items()}
    return datos


@pytest.fixture(scope="module")
def master_actual() -> dict:
    return generar_master()


def _comparar_caso(id_caso: str, esperado: dict, actual: dict) -> None:
    """Compara en profundidad y falla señalando caso y campo exactos."""
    for campo in sorted(set(esperado) | set(actual)):
        if campo not in esperado:
            pytest.fail(f"[{id_caso}] campo nuevo no presente en el master: {campo}={actual[campo]!r}")
        if campo not in actual:
            pytest.fail(f"[{id_caso}] campo del master desaparecido: {campo}={esperado[campo]!r}")
        valor_esperado, valor_actual = esperado[campo], actual[campo]
        if campo == "predictions":
            for horizonte in sorted(set(valor_esperado) | set(valor_actual), key=str):
                h = str(horizonte)
                if horizonte not in valor_actual:
                    pytest.fail(f"[{id_caso}] horizonte {h} desaparecido (master: {valor_esperado[horizonte]!r})")
                if horizonte not in valor_esperado:
                    pytest.fail(f"[{id_caso}] horizonte {h} nuevo (actual: {valor_actual[horizonte]!r})")
                for variable in sorted(set(valor_esperado[horizonte]) | set(valor_actual[horizonte])):
                    if variable not in valor_actual[horizonte]:
                        pytest.fail(f"[{id_caso}] variable {variable} desaparecida del horizonte {h}")
                    if variable not in valor_esperado[horizonte]:
                        pytest.fail(f"[{id_caso}] variable {variable} nueva en el horizonte {h}")
                    e, a = valor_esperado[horizonte][variable], valor_actual[horizonte][variable]
                    if e != a:
                        pytest.fail(f"[{id_caso}] horizonte {h}h, variable {variable}: master={e!r} vs actual={a!r}")
        elif valor_esperado != valor_actual:
            pytest.fail(f"[{id_caso}] campo {campo}: master={valor_esperado!r} vs actual={valor_actual!r}")


def test_congela_los_mismos_casos(master_guardado: dict, master_actual: dict):
    # CONGELA: el juego fijo de casos no cambia sin decisión de negocio.
    assert set(master_guardado["casos"]) == set(master_actual["casos"]), (
        f"casos master={sorted(master_guardado['casos'])} vs actual={sorted(master_actual['casos'])}"
    )


def test_congela_version_del_modelo(master_guardado: dict, master_actual: dict):
    # CONGELA: si cambia el md5 del artefacto, el master queda obsoleto →
    # requiere decisión de negocio documentada (reentrenamiento).
    assert master_actual["_meta"]["modelo_md5"] == master_guardado["_meta"]["modelo_md5"]


@pytest.mark.parametrize("id_caso", sorted(json.loads((MASTER_PATH).read_text(encoding="utf-8"))["casos"]))
def test_congela_salida_completa_del_caso(id_caso: str, master_guardado: dict, master_actual: dict):
    # CONGELA comportamiento actual: salida completa (todos los decimales).
    _comparar_caso(id_caso, master_guardado["casos"][id_caso], master_actual["casos"][id_caso])
