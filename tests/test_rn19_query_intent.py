"""RN-19 — Clasificación de intención por subcadenas con prioridad fija.

Fuente: specs/000-reconocimiento/reglas-de-negocio.md (RN-19) y
anomalía A-12 (subcadenas falsas). Congela el orden actual > consejo >
histórico > pronóstico > general y los falsos positivos por subcadena.
"""

from __future__ import annotations

import pytest

from src.domain.agent.value_objects.query_intent import IntentType, QueryIntent

# Casos de contraste del documento (RN-19):
CASOS_DOC = [
    # (consulta, intención esperada, weather_related esperado)
    ("I want to know the weather", IntentType.CURRENT_CONDITIONS, True),  # "now" dentro de "know"
    ("Will it rain in social media", IntentType.HISTORICAL, True),  # "media" antes que "rain"
    ("¿Lloverá mañana en Madrid?", IntentType.FORECAST, True),
    ("¿Qué tiempo hará en Madrid?", IntentType.FORECAST, True),
    ("Should I bring an umbrella?", IntentType.ADVICE, True),
    ("¿Llovió más el año pasado en Madrid?", IntentType.HISTORICAL, True),
    ("¿quién eres?", IntentType.GENERAL, False),
    ("hola", IntentType.GENERAL, False),
    ("How hot is it right now in Berlin?", IntentType.CURRENT_CONDITIONS, True),
    ("¿Qué tiempo hará en madrid?", IntentType.FORECAST, True),  # el intent no distingue caja
    ("What's the weather?", IntentType.GENERAL, False),  # sin palabra clave: comodín GENERAL
]

# Fronteras de orden de evaluación (gana la primera lista que haga match).
CASOS_ORDEN = [
    # ahora > consejo: "Should I bring an umbrella right now" contiene
    # "right now" (current) y "should i"/"bring" (advice) → gana CURRENT.
    ("Should I bring an umbrella right now?", IntentType.CURRENT_CONDITIONS),
    # ahora > histórico: "now" gana aunque haya "past".
    ("How is the weather now compared to the past?", IntentType.CURRENT_CONDITIONS),
    # consejo > histórico: "should i" gana sobre "average".
    ("Should I check the average temperature?", IntentType.ADVICE),
    # consejo > pronóstico.
    ("Will it rain? Should I wear a jacket?", IntentType.ADVICE),
    # histórico > pronóstico: "yesterday" gana sobre "rain".
    ("Did it rain yesterday?", IntentType.HISTORICAL),
    # histórico > pronóstico: "media" (subcadena) gana sobre "rain"/"will".
    ("Will it rain in social media?", IntentType.HISTORICAL),
    # pronóstico como comodín: solo palabras de forecast → FORECAST.
    ("Will it rain?", IntentType.FORECAST),
    (" tomorrow ", IntentType.FORECAST),
    # sin ninguna palabra → GENERAL.
    ("12345", IntentType.GENERAL),
]


@pytest.mark.parametrize("consulta,esperada,related", CASOS_DOC, ids=[c[0][:40] for c in CASOS_DOC])
def test_congela_clasificacion_de_casos_del_documento(consulta: str, esperada: IntentType, related: bool):
    # CONGELA comportamiento actual (transcrito 2026-11-14).
    qi = QueryIntent.from_query(consulta)
    assert qi.intent_type is esperada
    assert qi.is_weather_related is related
    assert qi.raw_query == consulta
    assert qi.confidence == 1.0  # valor por defecto, nunca calculado


@pytest.mark.parametrize("consulta,esperada", CASOS_ORDEN, ids=[c[0][:40] for c in CASOS_ORDEN])
def test_congela_orden_de_evaluacion(consulta: str, esperada: IntentType):
    # RN-19: ahora > consejo > histórico > pronóstico > general.
    assert QueryIntent.from_query(consulta).intent_type is esperada


def test_congela_query_vacia_o_espacios_rechazada_en_from_query():
    # CONGELA comportamiento actual: la validación del value object dispara
    # antes de clasificar; no hay intención para cadena vacía o de espacios.
    for consulta in ["", "   "]:
        with pytest.raises(ValueError) as exc:
            QueryIntent.from_query(consulta)
        assert str(exc.value) == "raw_query must not be empty"


class TestValidacionDeQueryIntent:
    # Congela las invariantes del value object.

    def test_congela_rechazo_de_query_vacia(self):
        with pytest.raises(ValueError) as exc:
            QueryIntent(intent_type=IntentType.GENERAL, raw_query="   ")
        assert str(exc.value) == "raw_query must not be empty"

    def test_congela_rechazo_de_confidencia_fuera_de_rango(self):
        with pytest.raises(ValueError) as exc:
            QueryIntent(intent_type=IntentType.GENERAL, raw_query="x", confidence=1.1)
        assert str(exc.value) == "confidence must be between 0.0 and 1.0"
        with pytest.raises(ValueError):
            QueryIntent(intent_type=IntentType.GENERAL, raw_query="x", confidence=-0.1)

    @pytest.mark.parametrize("conf", [0.0, 1.0])
    def test_congela_confidencia_en_extremos_acepta(self, conf: float):
        assert QueryIntent(intent_type=IntentType.GENERAL, raw_query="x", confidence=conf).confidence == conf

    def test_congela_is_weather_related_por_tipo(self):
        # FORECAST/CURRENT/HISTORICAL/ADVICE sí; GENERAL no.
        for tipo, esperado in [
            (IntentType.FORECAST, True),
            (IntentType.CURRENT_CONDITIONS, True),
            (IntentType.HISTORICAL, True),
            (IntentType.ADVICE, True),
            (IntentType.GENERAL, False),
        ]:
            assert QueryIntent(intent_type=tipo, raw_query="q").is_weather_related is esperado
