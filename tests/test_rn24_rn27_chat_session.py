"""RN-24, RN-27 y anomalías A-18/A-23 — ciclo de vida de ChatSession.

Fuente: reglas-de-negocio.md (RN-24, RN-27), flujo-aplicacion.md (§5) y
registro-de-anomalias.md (A-18: eventos que se pierden y etiqueta
ml_prediction que nunca coincide).
"""

from __future__ import annotations

import uuid

import pytest

from src.domain.agent.aggregate import ChatSession
from src.domain.agent.value_objects import ContextChunk, RetrievedDocument


def chunk_weather() -> ContextChunk:
    return ContextChunk(
        chunk_type="weather_and_prediction",
        content="Current conditions: temp=18.5°C...",
        source="open_meteo_and_ml",
        metadata={"city": "Madrid"},
    )


def chunk_rag(titulo: str = "doc") -> ContextChunk:
    return ContextChunk(
        chunk_type="rag_document",
        content="contenido",
        source="knowledge_base",
        metadata={"title": titulo, "category": "general", "similarity_score": 0.9},
    )


class TestRN24UnaPreguntaUnaRespuesta:
    # RN-24: una conversación es una pregunta y una respuesta.

    def test_congela_rechazo_de_query_vacia(self):
        with pytest.raises(ValueError) as exc:
            ChatSession(query_text="")
        assert str(exc.value) == "query_text must not be empty"
        with pytest.raises(ValueError):
            ChatSession(query_text="   ")

    def test_congela_doble_respuesta_prohibida(self):
        sesion = ChatSession(query_text="¿Qué tiempo hará en Madrid?")
        sesion.generate_response("respuesta")
        with pytest.raises(ValueError) as exc:
            sesion.generate_response("otra")
        assert str(exc.value) == "Response has already been generated"

    def test_congela_contexto_tras_respuesta_prohibido(self):
        sesion = ChatSession(query_text="q")
        sesion.generate_response("respuesta")
        with pytest.raises(ValueError) as exc:
            sesion.add_context(chunk_weather())
        assert str(exc.value) == "Cannot add context after response is generated"
        with pytest.raises(ValueError) as exc:
            sesion.add_rag_documents([])
        assert str(exc.value) == "Cannot add context after response is generated"

    def test_congela_identidad_de_sesion(self):
        sesion = ChatSession(query_text="q")
        assert isinstance(sesion.id, uuid.UUID)
        assert sesion.created_at.tzinfo is not None  # UTC por defecto
        assert sesion.response_text is None
        assert sesion.is_responded is False
        sesion.generate_response("r")
        assert sesion.is_responded is True
        assert sesion.response_text == "r"


class TestRN27EventosQueSePierden:
    # RN-27/A-18: dos eventos por conversación, recogidos y descartados.

    def test_congela_eventos_recibido_y_generado(self):
        sesion = ChatSession(query_text="¿Lloverá en Madrid?")
        eventos = sesion.pop_events()
        assert len(eventos) == 1  # QueryReceived al crear
        assert eventos[0].query_text == "¿Lloverá en Madrid?"
        assert eventos[0].session_id == str(sesion.id)

        sesion.add_context(chunk_weather())
        sesion.add_rag_documents([RetrievedDocument(title="t", content="c", category="g", similarity_score=0.5)])
        sesion.generate_response("respuesta")
        eventos = sesion.pop_events()
        assert len(eventos) == 1  # ResponseGenerated
        assert eventos[0].response_text == "respuesta"
        assert eventos[0].used_rag is True
        assert eventos[0].retrieved_doc_count == 1

    def test_congela_used_ml_prediction_siempre_falso_con_etiqueta_real(self):
        # CONGELA comportamiento actual (A-18): el handler etiqueta el chunk
        # como "weather_and_prediction" pero el agregado busca
        # "ml_prediction" → used_ml_prediction es SIEMPRE False.
        sesion = ChatSession(query_text="q")
        sesion.add_context(chunk_weather())
        sesion.generate_response("r")
        evento = sesion.pop_events()[-1]  # el último es ResponseGenerated
        assert evento.used_ml_prediction is False
        assert evento.used_rag is False

    def test_congela_used_ml_prediction_verdadero_solo_con_etiqueta_muerta(self):
        # Solo un chunk etiquetado exactamente "ml_prediction" (etiqueta que
        # ningún código de producción usa) activa el indicador.
        sesion = ChatSession(query_text="q")
        sesion.add_context(ContextChunk(chunk_type="ml_prediction", content="x", source="ml", metadata={}))
        sesion.generate_response("r")
        assert sesion.pop_events()[-1].used_ml_prediction is True

    def test_congela_pop_events_vacia_la_coleccion(self):
        sesion = ChatSession(query_text="q")
        assert len(sesion.pop_events()) == 1
        assert sesion.pop_events() == []  # segunda llamada: vacía


class TestResumenDeContexto:
    # Congela get_context_summary (método sin consumidor en runtime, A-23).

    def test_congela_resumen_sin_contexto_rechaza(self):
        sesion = ChatSession(query_text="q")
        with pytest.raises(ValueError) as exc:
            sesion.get_context_summary()
        assert str(exc.value) == "No context available for this session"

    def test_congela_resumen_con_contexto(self):
        sesion = ChatSession(query_text="q")
        sesion.add_context(chunk_weather())
        sesion.add_rag_documents([RetrievedDocument(title="t", content="c", category="g", similarity_score=0.5)])
        resumen = sesion.get_context_summary()
        assert resumen == (
            "weather_and_prediction: 1 item(s)\n"
            "  [open_meteo_and_ml] Current conditions: temp=18.5°C...\n"
            "rag_document: 1 item(s)\n"
            "  [knowledge_base] c"
        )

    def test_congela_truncado_a_100_caracteres(self):
        sesion = ChatSession(query_text="q")
        sesion.add_context(
            ContextChunk(
                chunk_type="rag_document",
                content="x" * 150,
                source="knowledge_base",
                metadata={"title": "t", "category": "g", "similarity_score": 0.5},
            )
        )
        resumen = sesion.get_context_summary()
        # CONGELA: el preview es de 100 caracteres + "..." (no 97+3).
        assert ("  [knowledge_base] " + "x" * 100 + "...") in resumen
