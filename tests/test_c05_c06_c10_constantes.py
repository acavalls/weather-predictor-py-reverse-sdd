"""C-05, C-06 y C-10 — constantes de contrato duplicadas.

Fuente: contradiccion-05-ruta-modelo-default.md,
contradiccion-06-horizontes-hardcodeados.md y
contradiccion-10-constantes-duplicadas.md.
Congela CADA copia por separado: hoy conviven valores distintos para "la
ruta del modelo" y listas de horizontes repetidas en seis sitios.
"""

from __future__ import annotations

import inspect

from src.application.ask_agent.handler import AskAgentHandler
from src.application.predict.handler import PredictHandler
from src.infrastructure.config.settings import Settings
from src.infrastructure.ml.local_predictor import LocalPredictor

from .conftest import predictor_cargado


class TestC05RutaDelModeloTresValores:
    # C-05: tres valores de "dónde está el modelo" conviven en el sistema.

    def test_congela_default_del_predictor(self):
        predictor = LocalPredictor()
        assert predictor._default_model_path == "models/model.pkl"

    def test_congela_default_del_handler_de_chat(self):
        # CONGELA: el handler del chat usa "model.pkl" (¡otra ruta!).
        handler = AskAgentHandler(
            weather_provider=None,
            model_predictor=None,
            feature_extractor=None,
            vector_store=None,
            embedder=None,
            llm_provider=None,
            logger=None,
        )
        assert handler._model_path == "model.pkl"

    def test_congela_default_del_handler_de_predict(self):
        handler = PredictHandler(
            weather_provider=None,
            model_predictor=None,
            feature_extractor=None,
        )
        assert handler._model_path == "model.pkl"

    def test_congela_setting_oficial(self):
        assert Settings().model_path == "models/model.pkl"


class TestC06HorizontesRepetidos:
    # C-06: [6, 12, 24] repetido en el servicio; el modelo entrenó 6 más.

    def test_congela_horizontes_del_modelo(self):
        _, meta = predictor_cargado()
        assert meta.horizons == [6, 12, 24, 48, 72, 168]

    def test_congela_horizontes_de_la_api(self):
        from src.infrastructure.http.routes.predict import PredictRequest

        assert PredictRequest(location="Madrid").horizons == [6, 12, 24]

    def test_congela_horizontes_del_comando(self):
        from src.application.predict.command import PredictCommand

        assert PredictCommand(city="Madrid").horizons == [6, 12, 24]

    def test_congela_horizontes_del_handler_predict(self):
        handler = PredictHandler(weather_provider=None, model_predictor=None, feature_extractor=None)
        assert handler._default_horizons == [6, 12, 24]

    def test_congela_horizontes_literal_en_el_handler_chat(self):
        # CONGELA: el chat fija [6, 12, 24] dos veces dentro de
        # _gather_weather_context (extract y predict), literal en el código.
        fuente = inspect.getsource(AskAgentHandler._gather_weather_context)
        assert fuente.count("horizons=[6, 12, 24]") == 2


class TestC10ConstantesDuplicadas:
    # C-10: modelo de embeddings, dimensión y parámetros LLM en varios sitios.

    def test_congela_modelo_de_embeddings_en_dos_sitios(self):
        from src.infrastructure.embedding.local_embedder import LocalEmbedder

        assert Settings().embedder_model == "all-MiniLM-L6-v2"  # settings (sin consumidor)
        embedder = LocalEmbedder()
        # El default real del adaptador (el settings no se cablea en di.py):
        assert embedder._model_name == "all-MiniLM-L6-v2"

    def test_congela_dimension_de_embeddings(self):
        from src.infrastructure.persistence.models.knowledge_base import KnowledgeBaseModel

        # ORM: columna de 384 dimensiones.
        col = KnowledgeBaseModel.__table__.c["embedding"]
        assert col.type.dim == 384

    def test_congela_parametros_llm(self):
        from src.infrastructure.llm.opencode_go_llm import OpenCodeGoLLM

        assert Settings().llm_model == "mimo-v2.6-flash"
        assert Settings().llm_api_url == "https://opencode.ai/zen/go/v1"
        # La instancia duplica los defaults del settings (y di.py los repite):
        llm = OpenCodeGoLLM(api_key="", base_url=Settings().llm_api_url)
        assert llm._model == "mimo-v2.6-flash"
        # CONGELA (RN-26): temperatura 0.7 y máximo 1024 tokens, literales
        # dentro de generate(); la sesión es un UUID por instancia.
        fuente = inspect.getsource(OpenCodeGoLLM.generate)
        assert '"temperature": 0.7' in fuente
        assert '"max_tokens": 1024' in fuente
        llm2 = OpenCodeGoLLM(api_key="")
        assert llm2._session_id != llm._session_id  # UUID distinto por instancia
        assert llm._base_url == "https://opencode.ai/zen/go/v1"
