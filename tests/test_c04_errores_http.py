"""C-04 — capa HTTP duplicada y asimétrica entre rutas.

Fuente: specs/000-reconocimiento/contradiccion-04-mapeo-errores-http-duplicado.md
y reglas-de-negocio.md (RN-05: el 400 con mensaje técnico interno).
Congela CADA implementación por separado: /chat devuelve el texto de la
excepción interna en el 500; /predict no tiene manejador genérico (500
genérico de FastAPI). Ambas mapean NotFoundError→404 y ValueError→400.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.domain.shared.errors import NotFoundError
from src.infrastructure.http.routes import chat as ruta_chat
from src.infrastructure.http.routes import predict as ruta_predict


class _UseCaseQueFalla:
    def __init__(self, excepcion: Exception) -> None:
        self._excepcion = excepcion

    async def execute(self, command):
        raise self._excepcion


def _app_chat(use_case) -> TestClient:
    app = FastAPI()
    app.include_router(ruta_chat.router)
    app.dependency_overrides[ruta_chat.get_ask_agent_use_case] = lambda: use_case
    return TestClient(app)


def _app_predict(use_case) -> TestClient:
    app = FastAPI()
    app.include_router(ruta_predict.router)
    app.dependency_overrides[ruta_predict.get_predict_use_case] = lambda: use_case
    # raise_server_exceptions=False: permite observar el 500 tal cual lo ve
    # el cliente (sin reventar el propio test).
    return TestClient(app, raise_server_exceptions=False)


class TestMapeoComun404y400:
    def test_congela_chat_404_con_texto_de_la_excepcion(self):
        cliente = _app_chat(_UseCaseQueFalla(NotFoundError("City not found: Ahoraqueloscilae")))
        respuesta = cliente.post("/chat", json={"query": "tiempo en Ahoraqueloscilae"})
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "City not found: Ahoraqueloscilae"}

    def test_congela_predict_404_con_texto_de_la_excepcion(self):
        cliente = _app_predict(_UseCaseQueFalla(NotFoundError("City not found: X")))
        respuesta = cliente.post("/predict", json={"location": "X"})
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "City not found: X"}

    def test_congela_chat_400_con_texto_de_la_excepcion(self):
        cliente = _app_chat(_UseCaseQueFalla(ValueError("query_text must not be empty")))
        respuesta = cliente.post("/chat", json={"query": "   "})
        # Nota: "   " pasa Pydantic (C-03) y muere en el comando → 400.
        assert respuesta.status_code == 400
        assert respuesta.json() == {"detail": "query_text must not be empty"}

    def test_congela_predict_400_con_mensaje_tecnico_interno(self):
        # RN-05: el 400 de horizontes vacíos expone el mensaje interno.
        cliente = _app_predict(_UseCaseQueFalla(ValueError("Prediction result must contain at least one prediction")))
        respuesta = cliente.post("/predict", json={"location": "Madrid", "horizons": [999]})
        assert respuesta.status_code == 400
        assert respuesta.json() == {"detail": "Prediction result must contain at least one prediction"}


class TestAsimetriaDel500:
    def test_congela_chat_500_expone_el_texto_interno(self):
        # CONGELA comportamiento actual: /chat sí tiene manejador genérico
        # y devuelve detail=str(exc) con el texto de la excepción interna.
        cliente = _app_chat(_UseCaseQueFalla(RuntimeError("fallo interno de BD")))
        respuesta = cliente.post("/chat", json={"query": "tiempo en Madrid"})
        assert respuesta.status_code == 500
        assert respuesta.json() == {"detail": "fallo interno de BD"}

    def test_congela_predict_500_generico_sin_detalle(self):
        # CONGELA comportamiento actual: /predict NO tiene manejador
        # genérico → el cliente recibe el 500 por defecto de FastAPI, en
        # texto plano y sin JSON.
        cliente = _app_predict(_UseCaseQueFalla(RuntimeError("fallo interno de BD")))
        respuesta = cliente.post("/predict", json={"location": "Madrid"})
        assert respuesta.status_code == 500
        assert respuesta.text == "Internal Server Error"


class TestContratosDeEntradaHTTP:
    def test_congela_chat_422_para_query_vacia(self):
        cliente = _app_chat(_UseCaseQueFalla(AssertionError("no debe llegarse a ejecutar")))
        respuesta = cliente.post("/chat", json={"query": ""})
        assert respuesta.status_code == 422  # Pydantic min_length=1

    def test_congela_forma_de_respuesta_de_chat(self):
        class _UseCaseOk:
            async def execute(self, command):
                from src.application.ask_agent.port import AskAgentResult

                return AskAgentResult(response="hola", session_id="session-123", events=[])

        cliente = _app_chat(_UseCaseOk())
        respuesta = cliente.post("/chat", json={"query": "tiempo en Madrid"})
        assert respuesta.status_code == 200
        assert respuesta.json() == {"response": "hola", "session_id": "session-123"}

    def test_congela_horizontes_por_defecto_de_la_peticion(self):
        from src.infrastructure.http.routes.predict import PredictRequest

        assert PredictRequest(location="Madrid").horizons == [6, 12, 24]

    def test_congela_horizontes_float_rechazados(self):
        cliente = _app_predict(_UseCaseQueFalla(AssertionError("no debe llegarse a ejecutar")))
        respuesta = cliente.post("/predict", json={"location": "Madrid", "horizons": [6.5]})
        assert respuesta.status_code == 422  # List[int] estricto de Pydantic
