"""RN-22 y A-42 — extracción de ciudad por patrones "in/at/for/en".

Fuente: specs/000-reconocimiento/reglas-de-negocio.md (RN-22) y anomalía
nueva A-42 (registrada durante la caracterización): el patrón no admite
ñ/ã, de modo que "São Paulo" y "A Coruña" NO se extraen.
"""

from __future__ import annotations

import pytest

from src.application.ask_agent.handler import AskAgentHandler

# Casos de contraste del documento (RN-22).
CASOS_DOC = [
    ("¿Qué tiempo hará en Madrid?", "Madrid"),  # patrón "en" captura "Madrid"
    ("¿Qué tiempo hará en madrid?", None),  # minúscula: sin match
    ("Rain in Spain and fog en Paris", "Spain"),  # gana el primer patrón ("in")
]

CASOS_ADICIONALES = [
    ("Weather at New York tomorrow", "New York"),  # multi-palabra
    ("Pronóstico for Mexico City", "Mexico City"),
    ("en Tokyo que tal", "Tokyo"),  # "en" funciona aunque la frase siga en español
    ("¿Lloverá mañana en Múnich?", "Múnich"),  # ú sí está en la clase de caracteres
    # CONGELA comportamiento actual (A-42): ã y ñ NO están en la clase
    # [A-ZÁÉÍÓÚÜ][a-záéíóúü]+ → la ciudad no se extrae.
    ("Pronóstico for São Paulo", None),
    ("¿Qué tiempo hará en A Coruña?", None),
    ("en A Coruña", None),
    ("Hello world", None),  # sin patrón
    ("", None),  # vacía
]


CASOS_TODOS = CASOS_DOC + CASOS_ADICIONALES


@pytest.mark.parametrize("consulta,esperada", CASOS_TODOS, ids=[c[0][:40] for c in CASOS_TODOS])
def test_congela_extraccion_de_ciudad(consulta: str, esperada):
    # CONGELA comportamiento actual (transcrito 2026-11-14).
    assert AskAgentHandler._extract_city(consulta) == esperada


def test_congela_orden_de_patrones_in_antes_que_en():
    # RN-22: los patrones se prueban en orden in/at/for/en y gana el primero.
    # "in" aparece antes en la frase y en la lista → "Spain", no "Paris".
    assert AskAgentHandler._extract_city("Rain in Spain and fog en Paris") == "Spain"


def test_congela_extraccion_multi_palabra_con_tilde():
    # Los acentos de la clase aceptada sí funcionan (Múnich, México).
    assert AskAgentHandler._extract_city("for México") == "México"
