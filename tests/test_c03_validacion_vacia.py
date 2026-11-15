"""C-03 — validación de entrada vacía en dos capas con criterios distintos.

Fuente: specs/000-reconocimiento/contradiccion-03-validacion-vacia-doble-capas.md.
Congela CADA implementación por separado: la capa HTTP (Pydantic,
min_length=1, no recorta espacios) y la capa de aplicación (comando de
dominio, que sí recorta).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.ask_agent.command import AskAgentCommand
from src.application.predict.command import PredictCommand
from src.infrastructure.http.routes.chat import ChatRequest
from src.infrastructure.http.routes.predict import PredictRequest


class TestCapaHTTPPydantic:
    # Implementación A: min_length=1, SIN strip → "   " pasa.

    def test_congela_cadena_vacia_rechazada_en_chat(self):
        with pytest.raises(ValidationError):
            ChatRequest(query="")

    def test_congela_solo_espacios_aceptada_en_chat(self):
        # CONGELA comportamiento actual: "   " supera la capa HTTP.
        assert ChatRequest(query="   ").query == "   "

    def test_congela_location_vacia_rechazada_en_predict(self):
        with pytest.raises(ValidationError):
            PredictRequest(location="")

    def test_congela_solo_espacios_aceptada_en_predict(self):
        assert PredictRequest(location="   ").location == "   "


class TestCapaAplicacionComando:
    # Implementación B: el comando de dominio recorta espacios.

    @pytest.mark.parametrize("texto", ["", "   "])
    def test_congela_ask_agent_command_rechaza_vacio_y_espacios(self, texto: str):
        with pytest.raises(ValueError) as exc:
            AskAgentCommand(query_text=texto)
        assert str(exc.value) == "query_text must not be empty"

    def test_congela_predict_command_rechaza_ciudad_vacia(self):
        with pytest.raises(ValueError) as exc:
            PredictCommand(city="", horizons=[6])
        assert str(exc.value) == "City name cannot be empty"

    def test_congela_predict_command_rechaza_horizontes_vacios(self):
        with pytest.raises(ValueError) as exc:
            PredictCommand(city="Madrid", horizons=[])
        assert str(exc.value) == "At least one horizon is required"

    def test_congela_predict_command_horizontes_por_defecto(self):
        # C-06: el default del comando es [6, 12, 24].
        assert PredictCommand(city="Madrid").horizons == [6, 12, 24]

    def test_congela_divergencia_entre_capas(self):
        # C-03: la misma entrada "   " pasa la capa HTTP y muere en la de
        # aplicación; "" muere en ambas. Congelado arriba en ambos bloques.
        assert ChatRequest(query="   ").query == "   "
        with pytest.raises(ValueError):
            AskAgentCommand(query_text="   ")
