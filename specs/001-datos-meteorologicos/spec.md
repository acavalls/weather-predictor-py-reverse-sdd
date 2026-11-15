# Feature Specification: SPEC-01 — Datos meteorológicos en tiempo real

**Feature Branch**: `specs/001-datos-meteorologicos` (sin rama git: hook `before_specify` saltado por decisión del usuario, ver acta de método)

**Created**: 2026-11-14

**Status**: Draft

**Input**: Especificación inversa de `propuesta-particion-specs.md` (PARTE 2, SPEC-01). Spec de ingeniería inversa: documenta el comportamiento EXISTENTE de la resolución de ubicación y la obtención de datos meteorológicos en tiempo real. No es una feature nueva: es la especificación formal de lo que el sistema YA hace, para que sirva de contrato en la modernización.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El sistema resuelve una ciudad con el primer resultado del servicio, en inglés (Priority: P1)

El negocio pide el tiempo de una ciudad ("Múnich") y el sistema pregunta al servicio de geocodificación con `count=1` y `language=en`, usando el primer resultado aunque existan varias ciudades con ese nombre (RN-01; `open_meteo_adapter.py:64-81`, `results[0]` en `:76-81`).

**Why this priority**: sin ubicación resuelta no hay dato meteorológico ni predicción: es el primer eslabón de ambos flujos de negocio.

**Independent Test**: verificable contractualmente con la evidencia del código (IO de red fuera de la suite); la convención de parámetros queda congelada en esta spec.

**Acceptance Scenarios**:

1. **Given** la petición "Múnich", **When** el sistema geocodifica, **Then** el servicio recibe `name=Múnich, count=1, language=en` y se usa `results[0]`.
2. **Given** un nombre con varias coincidencias, **When** el sistema geocodifica, **Then** toma el primer resultado sin presentar alternativas.

---

### User Story 2 - Ciudad desconocida: la petición se rechaza con 404 (Priority: P1)

Si el servicio no reconoce la ciudad, no hay predicción ni respuesta: el negocio recibe un rechazo "no encontrado" (RN-02; `open_meteo_adapter.py:72-74`, mapeo a 404 en `chat.py:67-72` y `predict.py:90-94`).

**Why this priority**: define el contrato de error más frecuente del dato meteorológico.

**Independent Test**: contrato HTTP congelado por `tests/test_c04_errores_http.py` (404 con `detail=str(exc)` en ambas rutas).

**Acceptance Scenarios**:

1. **Given** `geocode("Ahoraqueloscilae")` con `results` vacío, **When** el adaptador evalúa la respuesta, **Then** lanza `NotFoundError` y la ruta devuelve HTTP 404 con `detail` = texto de la excepción.

---

### User Story 3 - Magnitud ausente: se inventa un valor neutral y se sigue adelante (Priority: P2)

Cuando el proveedor no trae una variable del tiempo actual, el sistema la sustituye por 0 (temperatura, humedad, viento, nubes, lluvia) o 1013 hPa (presión) y continúa (RN-03; `open_meteo_adapter.py:115-122`).

**Why this priority**: es una decisión DUDOSA (¿política de negocio o comodín técnico?) que debe ratificarse; el comportamiento no cambia hasta esa ratificación.

**Independent Test**: IO de red fuera de la suite; verificación contractual con evidencia de línea. La decisión requiere ratificación real del negocio (acta no la cubre).

**Acceptance Scenarios**:

1. **Given** una respuesta de Open-Meteo sin `cloud_cover`, **When** el adaptador construye `CurrentWeather`, **Then** el modelo y el resumen trabajan con "nubes 0,0 %" aunque el cielo esté cubierto (el comentario `open_meteo_adapter.py:92-93` promete "all measured variables": discrepancia documentada).

---

### User Story 4 - Límites físicos de las magnitudes, con fronteras inclusivas (Priority: P1)

Toda magnitud debe caer en su rango físico; los extremos son válidos (RN-04; `weather/value_objects/__init__.py`). Temperatura [-100, 100] °C; humedad [0, 100] %; presión [870, 1084] hPa; precipitación ≥ 0 mm; viento ≥ 0 km/h; nubes [0, 100] %; latitud [-90, 90]; longitud [-180, 180].

**Why this priority**: es la única parte del dominio ejecutable sin red y protege el dato de entrada del modelo.

**Independent Test**: `tests/test_rn04_value_objects.py` — los tres puntos por los dos lados de cada umbral, con mensajes de error exactos.

**Acceptance Scenarios**:

1. **Given** `Temperature(-100.0)`, **When** se valida, **Then** es válida; con `-100.1` rompe con "Temperature too low: -100.1°C".
2. **Given** `Pressure(870)` y `Pressure(1084)`, **When** se validan, **Then** pasan; con 869.9/1084.1 rompen con "Pressure out of range: … hPa".
3. **Given** `Precipitation(0)` y `WindSpeed(0)`, **When** se validan, **Then** pasan (cero es válido; solo lo negativo rompe).

---

### Edge Cases

- Latitud/longitud en los extremos exactos (±90/±180 válidos; 90.1/180.1 rompen).
- Humedad 0 y 100 válidas; -0.1 y 100.1 rompen.
- Temperatura -273 °C rompe (el límite es -100, no el cero absoluto); negativas dentro de rango pasan.
- Formatos de texto congelados: "18.5°C", "62.0%", "1013.0 hPa", "0.0 mm", "12.3 km/h", "40.0%", "Madrid (40.4168, -3.7038)".
- Ciudad con tildes aceptadas por el geocoder ("Múnich"); la extracción desde texto es de SPEC-003.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE geocodificar ciudades pidiendo `count=1` y `language=en`, y DEBE usar el primer resultado (`results[0]`). Evidencia: `open_meteo_adapter.py:64-81`.
- **FR-002**: El sistema DEBE rechazar con `NotFoundError` (HTTP 404) toda ciudad que el servicio no reconozca. Evidencia: `open_meteo_adapter.py:72-74`, `chat.py:67-72`, `predict.py:90-94`.
- **FR-003**: El sistema DEBE sustituir toda magnitud ausente por 0 (o 1013 hPa para presión) y continuar. Anomalía referenciada: RN-03 (DUDOSA; decisión a ratificar). Evidencia: `open_meteo_adapter.py:115-122`.
- **FR-004**: El sistema DEBE validar los límites físicos con fronteras inclusivas y los mensajes exactos congelados en `tests/test_rn04_value_objects.py`.
- **FR-005**: El sistema DEBE mantener los formatos de texto de los value objects (`__str__`) tal cual están congelados.
- **FR-006**: El sistema NO DEBE redondear ninguna magnitud en el contrato de datos (el redondeo de presentación es decisión de SPEC-002/acta §8).

### Key Entities

- **Location**: coordenadas con nombre opcional; valida lat/lon con límites inclusivos.
- **CurrentWeather**: agrupa las 6 magnitudes medidas + ubicación; alimenta a SPEC-002 (predicción) y SPEC-003 (chat).

## Success Criteria *(mandatory)*

- **SC-001**: 100 % de las fronteras de RN-04 congeladas y en verde en `tests/test_rn04_value_objects.py` (3 puntos por lado × 8 magnitudes).
- **SC-002**: el contrato de geocodificación (RN-01/RN-02) documentado con evidencia de fichero y línea, verificable por revisión (IO fuera de la suite).
- **SC-003**: la decisión RN-03 queda referenciada como pregunta a ratificar con el negocio (testigo con nombre y fecha).

## Assumptions

- El servicio de geocodificación es Open-Meteo y su contrato no cambia durante la fase de protección.
- Toda decisión de negocio citada procede del acta **simulada** (`specs/000-reconocimiento/acta-entrevista-negocio.md`, P1-P18 y §8, 2026-11-14) y requiere ratificación real.
- La extracción de ciudad desde texto libre NO es parte de esta spec (SPEC-003).

## Fuera de alcance

- Extracción de ciudad del texto del usuario y flujo conversacional → SPEC-003.
- Conversión de condiciones a características del modelo → SPEC-002.
- Ingesta del histórico y entrenamiento → SPEC-004.
- Configuración, errores HTTP transversales, persistencia → SPEC-005.
