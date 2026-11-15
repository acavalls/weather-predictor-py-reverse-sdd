"""RN-25 (composición del prompt) y RN-13/A-39 (sin redondeos).

Fuente: reglas-de-negocio.md (RN-25, RN-13). Congela el texto exacto del
prompt que recibe el LLM y el formato bruto (sin redondeo) del resumen
meteorológico del chat.
"""

from __future__ import annotations

from src.application.ask_agent.handler import AskAgentHandler
from src.domain.agent.aggregate import ChatSession
from src.domain.agent.value_objects import ContextChunk

from .conftest import TS_FIJO


class TestRN25ComposicionDelPrompt:
    # RN-25: system prompt (inglés, fijo) + contextos agrupados + pregunta.

    def test_congela_system_prompt_literal(self):
        assert AskAgentHandler._SYSTEM_PROMPT == (
            "You are a weather assistant. Answer the user's question using the "
            "provided context (weather data, ML predictions, and meteorological "
            "principles). Be concise, scientific, and helpful. If the context "
            "doesn't contain enough information, say so."
        )

    def test_congela_prompt_sin_contexto(self):
        sesion = ChatSession(query_text="¿quién eres?")
        prompt = AskAgentHandler._build_prompt(sesion, "¿quién eres?")
        assert prompt == (
            "You are a weather assistant. Answer the user's question using the "
            "provided context (weather data, ML predictions, and meteorological "
            "principles). Be concise, scientific, and helpful. If the context "
            "doesn't contain enough information, say so."
            "\n\n## User Query\n\n¿quién eres?"
        )

    def test_congela_prompt_con_contexto_weather_y_rag(self):
        sesion = ChatSession(query_text="¿Lloverá en Madrid?", created_at=TS_FIJO)
        sesion.add_context(
            ContextChunk(
                chunk_type="weather_and_prediction",
                content="Current conditions: temp=18.5°C...",
                source="open_meteo_and_ml",
                metadata={"city": "Madrid"},
            )
        )
        sesion.add_context(
            ContextChunk(
                chunk_type="rag_document",
                content="La presión baja indica inestabilidad.",
                source="knowledge_base",
                metadata={"title": "presion"},
            )
        )
        prompt = AskAgentHandler._build_prompt(sesion, "¿Lloverá en Madrid?")
        # CONGELA: secciones en orden de inserción, cabeceras con tipo y fuente.
        assert prompt == (
            "You are a weather assistant. Answer the user's question using the "
            "provided context (weather data, ML predictions, and meteorological "
            "principles). Be concise, scientific, and helpful. If the context "
            "doesn't contain enough information, say so."
            "\n\n## Context\n\n"
            "### weather_and_prediction (source: open_meteo_and_ml)\n"
            "Current conditions: temp=18.5°C...\n\n"
            "### rag_document (source: knowledge_base)\n"
            "La presión baja indica inestabilidad.\n\n"
            "## User Query\n\n¿Lloverá en Madrid?"
        )


class TestRN13SinRedondeos:
    # RN-13/A-39: el resumen del chat imprime el float SIN formatear.

    class _FakePrediction:
        # Sustituto mínimo de PredictionResult para el formateador.
        predictions = {
            6: {
                "temperature_2m": 18.5343994140625,
                "relative_humidity_2m": 60.13257982269474,
                "surface_pressure": 929.9966631445844,
            },
            12: {
                "temperature_2m": 1.8996718078228674,
                "relative_humidity_2m": 30.847444550600645,
                "surface_pressure": 786.5776309236345,
            },
        }

    class _FakeWeather:
        temperature = type("T", (), {"value": 18.5343994140625})()
        humidity = type("H", (), {"value": 62.0})()
        pressure = type("P", (), {"value": 1013.0})()
        wind_speed = type("W", (), {"value": 12.3})()
        cloud_cover = type("C", (), {"value": 40.0})()
        precipitation = type("Pr", (), {"value": 0.0})()

    def test_congela_resumen_sin_redondeo(self):
        # CONGELA comportamiento actual: todos los decimales que produce el
        # modelo salen tal cual (no hay round/format en la salida).
        resumen = AskAgentHandler._format_weather_summary(self._FakeWeather(), self._FakePrediction())
        assert resumen == (
            "Current conditions: temp=18.5343994140625°C, "
            "humidity=62.0%, "
            "pressure=1013.0hPa, "
            "wind=12.3km/h, "
            "cloud_cover=40.0%, "
            "precipitation=0.0mm\n"
            "\n"
            "ML Predictions:\n"
            "  6h: temp=18.5343994140625°C, humidity=60.13257982269474%, pressure=929.9966631445844hPa\n"
            "  12h: temp=1.8996718078228674°C, humidity=30.847444550600645%, pressure=786.5776309236345hPa"
        )

    def test_congela_n_a_para_variables_ausentes(self):
        class _PredVacio:
            predictions = {6: {"temperature_2m": 18.5}}  # faltan humidity/pressure

        resumen = AskAgentHandler._format_weather_summary(self._FakeWeather(), _PredVacio())
        # CONGELA: la ausencia se imprime como el literal "N/A".
        assert "  6h: temp=18.5°C, humidity=N/A%, pressure=N/AhPa" in resumen

    def test_congela_orden_de_horizontes_en_el_resumen(self):
        # Orden de inserción del dict (6, 12, 24), no ordenado numéricamente.
        class _PredDesorden:
            predictions = {
                24: {"temperature_2m": 3.0, "relative_humidity_2m": 1.0, "surface_pressure": 2.0},
                6: {"temperature_2m": 1.0, "relative_humidity_2m": 4.0, "surface_pressure": 5.0},
            }

        resumen = AskAgentHandler._format_weather_summary(self._FakeWeather(), _PredDesorden())
        lineas = resumen.splitlines()
        assert lineas[3].startswith("  24h:")
        assert lineas[4].startswith("  6h:")
