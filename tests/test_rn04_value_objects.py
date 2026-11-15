"""RN-04 — Límites físicos de las magnitudes (fronteras inclusivas).

Fuente: specs/000-reconocimiento/reglas-de-negocio.md (RN-04).
Para cada umbral se congelan los tres puntos por los dos lados:
justo debajo (rechaza), el valor exacto (acepta) y justo encima (rechaza).
Mensajes de error transcritos del código actual.
"""

from __future__ import annotations

import pytest

from src.domain.weather.value_objects import (
    CloudCover,
    Humidity,
    Location,
    Precipitation,
    Pressure,
    Temperature,
    WindSpeed,
)


class TestTemperatura:
    # RN-04: temperatura [-100, 100] °C, extremos válidos.

    def test_congela_justo_debajo_del_minimo_rechaza(self):
        # CONGELA comportamiento actual: -100.1 rompe, -100 pasa.
        with pytest.raises(ValueError) as exc:
            Temperature(-100.1)
        assert str(exc.value) == "Temperature too low: -100.1°C"

    def test_congela_minimo_exacto_acepta(self):
        assert Temperature(-100.0).value == -100.0

    def test_congela_maximo_exacto_acepta(self):
        assert Temperature(100.0).value == 100.0

    def test_congela_justo_encima_del_maximo_rechaza(self):
        with pytest.raises(ValueError) as exc:
            Temperature(100.1)
        assert str(exc.value) == "Temperature too high: 100.1°C"

    def test_congela_cero_acepta(self):
        assert Temperature(0.0).value == 0.0

    def test_congela_negativa_dentro_de_rango_acepta(self):
        assert Temperature(-50.0).value == -50.0

    def test_congela_negativa_fuera_de_rango_rechaza(self):
        # CONGELA: -273 °C rompe (el límite es -100, no el cero absoluto).
        with pytest.raises(ValueError) as exc:
            Temperature(-273.0)
        assert str(exc.value) == "Temperature too low: -273.0°C"


class TestHumedad:
    # RN-04: humedad [0, 100] %.

    @pytest.mark.parametrize("valor", [-0.1, 100.1])
    def test_congela_fuera_de_rango_rechaza(self, valor: float):
        with pytest.raises(ValueError) as exc:
            Humidity(valor)
        assert str(exc.value) == f"Humidity must be between 0 and 100, got {valor}%"

    @pytest.mark.parametrize("valor", [0.0, 100.0])
    def test_congela_extremos_aceptan(self, valor: float):
        assert Humidity(valor).value == valor


class TestPresion:
    # RN-04: presión [870, 1084] hPa.

    def test_congela_justo_debajo_rechaza(self):
        with pytest.raises(ValueError) as exc:
            Pressure(869.9)
        assert str(exc.value) == "Pressure out of range: 869.9 hPa"

    @pytest.mark.parametrize("valor", [870.0, 1084.0])
    def test_congela_extremos_aceptan(self, valor: float):
        assert Pressure(valor).value == valor

    def test_congela_justo_encima_rechaza(self):
        with pytest.raises(ValueError) as exc:
            Pressure(1084.1)
        assert str(exc.value) == "Pressure out of range: 1084.1 hPa"


class TestPrecipitacion:
    # RN-04: precipitación >= 0 mm (sin máximo).

    def test_congela_justo_debajo_rechaza(self):
        with pytest.raises(ValueError) as exc:
            Precipitation(-0.1)
        assert str(exc.value) == "Precipitation cannot be negative: -0.1 mm"

    def test_congela_cero_acepta(self):
        assert Precipitation(0.0).value == 0.0

    def test_congela_valor_grande_acepta(self):
        assert Precipitation(1e9).value == 1e9


class TestViento:
    # RN-04: viento >= 0 km/h (sin máximo).

    def test_congela_justo_debajo_rechaza(self):
        with pytest.raises(ValueError) as exc:
            WindSpeed(-0.1)
        assert str(exc.value) == "Wind speed cannot be negative: -0.1 km/h"

    def test_congela_cero_acepta(self):
        assert WindSpeed(0.0).value == 0.0


class TestNubes:
    # RN-04: nubes [0, 100] %.

    @pytest.mark.parametrize("valor", [-0.1, 100.1])
    def test_congela_fuera_de_rango_rechaza(self, valor: float):
        with pytest.raises(ValueError) as exc:
            CloudCover(valor)
        assert str(exc.value) == f"Cloud cover must be between 0 and 100, got {valor}%"

    @pytest.mark.parametrize("valor", [0.0, 100.0])
    def test_congela_extremos_aceptan(self, valor: float):
        assert CloudCover(valor).value == valor


class TestLocalizacion:
    # RN-04: latitud [-90, 90], longitud [-180, 180].

    @pytest.mark.parametrize("lat", [-90.1, 90.1])
    def test_congela_latitud_fuera_rechaza(self, lat: float):
        with pytest.raises(ValueError) as exc:
            Location(lat, 0.0)
        assert str(exc.value) == f"Latitude must be between -90 and 90, got {lat}"

    @pytest.mark.parametrize("lat", [-90.0, 90.0])
    def test_congela_latitud_extremos_aceptan(self, lat: float):
        assert Location(lat, 0.0).latitude == lat

    @pytest.mark.parametrize("lon", [-180.1, 180.1])
    def test_congela_longitud_fuera_rechaza(self, lon: float):
        with pytest.raises(ValueError) as exc:
            Location(0.0, lon)
        assert str(exc.value) == f"Longitude must be between -180 and 180, got {lon}"

    @pytest.mark.parametrize("lon", [-180.0, 180.0])
    def test_congela_longitud_extremos_aceptan(self, lon: float):
        assert Location(0.0, lon).longitude == lon

    def test_congela_str_con_nombre(self):
        assert str(Location(40.4168, -3.7038, "Madrid")) == "Madrid (40.4168, -3.7038)"

    def test_congela_str_sin_nombre(self):
        assert str(Location(40.4168, -3.7038)) == "(40.4168, -3.7038)"


class TestFormatosTexto:
    # Formato __str__ de cada value object, tal cual (RN-13: sin redondeo
    # en negocio; aquí el formato es fijo a 1 decimal).

    def test_congela_formato_str(self):
        assert str(Temperature(18.5343994140625)) == "18.5°C"  # __str__ sí redondea a 1 decimal
        assert str(Humidity(62.0)) == "62.0%"
        assert str(Pressure(1013.0)) == "1013.0 hPa"
        assert str(Precipitation(0.0)) == "0.0 mm"
        assert str(WindSpeed(12.3)) == "12.3 km/h"
        assert str(CloudCover(40.0)) == "40.0%"
