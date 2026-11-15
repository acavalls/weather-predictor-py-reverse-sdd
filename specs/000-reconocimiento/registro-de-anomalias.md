# Registro de anomalías — consolidación del reconocimiento

Registro único de hallazgos de la ingeniería inversa, según la constitución
(Principios II y III): nada se corrige, todo se registra con testigos.
Regla innegociable aplicada: **ninguna clasificación INTENCIONAL sin al
menos dos de los tres testigos (CÓDIGO, DATOS, NEGOCIO) a favor**; si falta
el testimonio del negocio o el veredicto de los datos, la entrada queda
**PENDIENTE** con la pregunta que la desbloquearía.

## Fuentes recorridas (sin huérfanas)

| Fuente | Estado | Contenido absorbido |
|---|---|---|
| `reglas-de-negocio.md` | existe | DUDOSAS (RN-03, RN-15, RN-21, RN-26), ACCIDENTALES (RN-05, RN-09, RN-10, RN-13, RN-18, RN-19, RN-27, RN-28), INTENCIONALES con historia de incidente (RN-07, RN-12 y reglas protegidas W1-W4/H3/H4) |
| `contradiccion-01..10-*.md` | existen (10) | C-01 a C-10 completas |
| `registro-riesgos.md` | existe | R1-R19 |
| `mapa-sistema.md` | existe | Zonas oscuras §4.1-§4.19 |
| `flujo-aplicacion.md` | existe | Casos A-J y duplicidades §6a-§6g |
| `memoria-historica.md` | existe | H1-H12, W1-W4 (discrepancias y "no tocar"), A1-A12 (abandonados) |
| Arqueología de datos | ejecutada 2026-11-14 (pandas sobre el CSV, joblib sobre `model.pkl`, lectura de bytes del binario); resultados citados como testigo DATOS | — |
| `acta-entrevista-negocio.md` | existe (entrevista **simulada**, 2026-11-14) | decisiones P1-P18; testigo NEGOCIO **no válido** hasta ratificación real |

## Correcciones a documentos previos, cerradas por la arqueología de datos

1. **RN-28 (hora UTC vs local) REFUTADA**: el fingerprint horario del CSV es
   UTC en las 10 ciudades (hora más cálida media: London 14, Tokyo 5,
   Sydney 3, NY 19, Mexico City 21, São Paulo 17, Mumbai 8, Berlin 14,
   Madrid 15, Cairo 12) y la inferencia también usa UTC
   (`predict/handler.py:75`). Entrenamiento e inferencia alineados. La
   SUPOSICIÓN "CSV en hora local" era falsa; **no es anomalía**.
2. **RN-09 CORREGIDA**: el artefacto tiene 44 `feature_columns` y ninguna de
   `dew_point`/`wind_direction` (testigo DATOS); el entrenamiento solo usó
   lags de las 6 variables objetivo (`train_model.py:36-43`); la constante
   `NUMERIC_FEATURES` (`train_model.py:48`) está definida y sin uso. No hay
   desplazamiento de distribución: hay cálculo muerto (→ A-38).
3. **RN-15 CERRADA**: CSV continuo (0 huecos horarios, 0 duplicados por
   ciudad en 263.040 filas) → los `shift(h)` del entrenamiento son h horas
   reales.
4. **Dos hallazgos nuevos de datos** (A-01, A-02): el split "temporal" es en
   realidad una partición por ciudades y Tokyo/São Paulo nunca entraron en
   el entrenamiento.

---

## Anomalías (ordenadas por impacto)

### A-01 — El split "temporal" 80/20 es en realidad una partición por ciudades

**Descripción**: el comentario promete un corte temporal ("time-aware: last
portion as test") pero el CSV está ordenado por bloques de ciudad y el
corte al 80 % cae exactamente al final del bloque de Sydney: el test son
solo São Paulo y Tokyo.

- **Testigos**: CÓDIGO ✓ (`train_model.py:165-171`, comentario + `iloc` sin
  shuffle; `train_model.py:22-34` orden de ciudades en el script de
  descarga); DATOS ✓ (263.040 = 10×26.304; `split_idx = 210.432 = 8×26.304`;
  OneHot del artefacto con solo 8 ciudades; `test_score` 0.3713 = métrica
  entre ciudades); NEGOCIO ✗. Fuentes: arqueología, mapa §4.12.
- **Clasificación**: **BUG HISTÓRICO CON DEPENDIENTES** (C-02/C-09 no
  aplican; contradicción comentario-código con el modelo y sus métricas como
  dependientes).
- **Dependientes**: `models/model.pkl`; el `test_score` 0.3713 publicado;
  cualquier decisión basada en esa métrica; Tokyo/São Paulo.
- **Tratamiento** (sin acordar; propuesta): corregir reentrenando (no
  retroactiva); mientras tanto especificar tal cual y documentar el
  significado real del test_score.
- **Decisión pendiente**: estrategia de split/reentrenamiento. Responsable:
  sin identificar.

### A-02 — Tokyo y São Paulo se predicen con codificación a ceros

**Descripción**: el codificador solo conoce 8 ciudades; peticiones para
Tokyo y São Paulo se codifican all-zeros y sus predicciones son
extrapolaciones de un modelo que nunca las vio.

- **Testigos**: CÓDIGO ✓ (`local_predictor.py:173-176`, `train_model.py:178`);
  DATOS ✓ (categorías OneHot: `['Berlin','Cairo','London','Madrid','Mexico
  City','Mumbai','New York','Sydney']`); NEGOCIO ✗. Fuentes: arqueología,
  W4/H5 (memoria), RN-07.
- **Clasificación**: **BUG HISTÓRICO CON DEPENDIENTES** (depende de A-01).
- **Dependientes**: usuarios de Tokyo y São Paulo vía `/chat` y `/predict`.
- **Tratamiento**: sin acordar; propuesta: documentar calidad desconocida,
  corregir con A-01 (no retroactiva).
- **Decisión pendiente**: ¿avisar a negocio de ciudades no soportadas?
  Responsable: sin identificar.

### A-03 — El chat predice con condiciones actuales nulas (C-01)

**Descripción**: la conversión del tiempo actual a características está
duplicada con convenciones incompatibles (`to_features()` vs
`_weather_to_conditions`); en el chat todas las características entran a 0.

- **Testigos**: CÓDIGO ✓ (`weather/repository/__init__.py:50-62`,
  `predict/handler.py:96-115`, `feature_extractor.py:63-77`,
  `ask_agent/handler.py:157`, `local_predictor.py:186-192`); DATOS ✓
  (experimento C-01: mismas condiciones reales de Madrid → divergencias de
  −4,4 a −6,3 °C y −32 a −44 pp de humedad entre `/chat` y `/predict`);
  NEGOCIO ✗. Fuentes: mapa §4.1, flujo §6a, RN-10, C-01.
- **Clasificación**: **BUG A SECAS** (sin señal de deliberación; contraste
  interno entre handlers).
- **Dependientes**: calidad de todas las respuestas conversacionales con
  ciudad; el prompt que consume el LLM.
- **Tratamiento**: sin acordar; propuesta: caracterizar primero y corregir
  en modernización (no retroactiva sobre el activo: solo código).
- **Decisión pendiente**: ninguna para clasificar.

### A-04 — Semántica de lags distinta entre entrenamiento e inferencia (C-02)

**Descripción**: el entrenamiento usa el valor de h horas antes y la
inferencia rellena todos los lags con el valor actual; el comentario promete
coincidencia con el entrenamiento.

- **Testigos**: CÓDIGO ✓ (`train_model.py:100` vs
  `feature_extractor.py:62-77`; comentario `:21`); DATOS ✓ (MAE actual vs
  h-antes: 4,00/5,48/1,86 °C para h=6/12/24; p90 hasta 10,8 °C; CSV
  continuo verificado); NEGOCIO ✗. Fuentes: RN-08, R3, flujo §6b, H12, C-02.
- **Clasificación**: **BUG HISTÓRICO CON DEPENDIENTES**.
- **Dependientes**: toda predicción servida; el test_score medido bajo la
  semántica de entrenamiento.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual (es el
  comportamiento protegido); alinear exige reentrenar o llevar histórico a
  runtime (no retroactiva).
- **Decisión pendiente**: ¿aceptar la aproximación como diseño oficial?
  Responsable: sin identificar.

### A-05 — Sin autenticación y con detalles internos en los errores

**Descripción**: los endpoints no tienen auth y los errores 500 devuelven
el texto de la excepción interna al cliente (asimétrico entre rutas, C-04).

- **Testigos**: CÓDIGO ✓ (`chat.py:79-84`, `predict.py:84-99` sin genérico,
  `main.py:23-30` sin middleware, `Makefile:9` `0.0.0.0`); DATOS/NEGOCIO ✗.
  Fuentes: R2, flujo §6c/C-04.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional) para la ausencia de autenticación (servicio interno en red de confianza declarada) **+ BUG A SECAS** para la exposición del texto de excepciones (no aceptada, a corregir en modernización).
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P4 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: cualquier cliente; postura de despliegue.
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: decidida en acta P4 (simulada): interno aceptado; texto de excepciones no. Responsable: sin identificar (ratificación real pendiente).
### A-06 — Ruta del modelo por defecto: tres valores distintos (C-05)

**Descripción**: `"models/model.pkl"` (predictor), `"model.pkl"` (handlers)
y `settings.model_path` conviven; el DI tapa la divergencia.

- **Testigos**: CÓDIGO ✓ (`local_predictor.py:44`,
  `ask_agent/handler.py:52`, `predict/handler.py:34`, `settings.py:14`,
  `di.py:77,89`); DATOS ✗; NEGOCIO ✗. Fuentes: C-05.
- **Clasificación**: **BUG A SECAS** (latente: `FileNotFoundError` en
  construcción manual de handlers, p. ej. los próximos tests).
- **Dependientes**: tests de caracterización; reutilización fuera de FastAPI.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual y unificar
  en modernización.
- **Decisión pendiente**: ninguna.

### A-07 — Horizontes no entrenados producen 400 con mensaje técnico

**Descripción**: se acepta cualquier entero como horizonte; los
desconocidos se filtran y si no queda ninguno se responde 400 con el texto
interno "Prediction result must contain at least one prediction".

- **Testigos**: CÓDIGO ✓ (`predict.py:32-35`, `local_predictor.py:223-224`,
  `ml/value_objects/__init__.py:126`, `predict.py:95-99`); DATOS ✓ (el
  artefacto tiene targets de 6/12/24/48/72/168 y ninguno más); NEGOCIO ✗.
  Fuentes: RN-05, R8, C-06.
- **Clasificación**: **BUG A SECAS**.
- **Dependientes**: clientes de `/predict` con horizontes custom.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual, validar en
  modernización.
- **Decisión pendiente**: ninguna.

### A-08 — Política de horizontes: la lista está hardcodeada en seis sitios (C-06)

**Descripción**: `[6,12,24]` repetido 5 veces en el servicio y
`[6,12,24,48,72,168]` en el modelo: el 50 % de los horizontes entrenados es
inalcanzable por API y no existe un único sitio donde vivan "los horizontes
de negocio".

- **Testigos**: CÓDIGO ✓ (`predict.py:32-35`, `command.py:19`,
  `predict/handler.py:41`, `ask_agent/handler.py:160,165`,
  `train_model.py:155`); DATOS ✓ (`horizons` del artefacto); NEGOCIO ✗.
  Fuentes: RN-11, mapa §4.19, C-06.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): horizontes oficiales de negocio **6/12/24 h**; 48/72/168 descartados del contrato de API (pueden seguir entrenándose pero no se exponen).
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P5 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: contrato de la API; futuros reentrenamientos.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P5 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-09 — Credenciales de BD por defecto en el repositorio

**Descripción**: `weather`/`weather` fijos en compose, settings y script de
ingesta.

- **Testigos**: CÓDIGO ✓ (`docker-compose.yml:6-8`, `settings.py:9`,
  `ingest_knowledge.py:351-354`); DATOS/NEGOCIO ✗. Fuentes: R1.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): aceptadas **solo para entorno local**; prohibido desplegar en producción sin sobreescribirlas; añadir a la checklist de despliegue.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P6 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: entornos locales; despliegues sin override.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P6 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-10 — La ingesta del RAG puede dejar la base de conocimiento vacía

**Descripción**: `--reset` confirma el borrado en una transacción y los
inserts van en otra; un fallo a medias deja la KB vacía.

- **Testigos**: CÓDIGO ✓ (`ingest_knowledge.py:412-419,426-438`); DATOS/
  NEGOCIO ✗. Fuentes: R6.
- **Clasificación**: **BUG A SECAS**.
- **Dependientes**: disponibilidad del RAG tras recargas fallidas.
- **Tratamiento**: sin acordar; propuesta: corregir en modernización
  (transacción única), caracterizar primero.
- **Decisión pendiente**: ninguna.

### A-11 — Dependencias usadas no declaradas en `requirements.txt`

**Descripción**: `joblib`, `tqdm`, `asyncpg`, `alembic` se usan y no están
declaradas.

- **Testigos**: CÓDIGO ✓ (`local_predictor.py:12`, `train_model.py:20,28`,
  `settings.py:9`, `Makefile:35-39` vs `requirements.txt:1-33`); DATOS ✓
  (pip list: están instaladas por vía transitiva/manual); NEGOCIO ✗.
  Fuentes: R4, mapa §4.10.
- **Clasificación**: **BUG A SECAS**.
- **Dependientes**: instalaciones limpias, CI.
- **Tratamiento**: sin acordar; propuesta: declarar (no añade nada nuevo:
  ya están en el venv).
- **Decisión pendiente**: ninguna.

### A-12 — El clasificador de intenciones confunde subcadenas

**Descripción**: coincidencias por subcadena producen intenciones falsas
("know" contiene "now" → estado actual; "social media" contiene "media" →
histórico).

- **Testigos**: CÓDIGO ✓ (`query_intent.py:165-176`, listas `:19-110`);
  DATOS/NEGOCIO ✗. Fuentes: RN-19 (parte ACCIDENTAL), flujo §6g.
- **Clasificación**: **BUG A SECAS**.
- **Dependientes**: qué flujo recibe cada pregunta.
- **Tratamiento**: sin acordar; propuesta: caracterizar con tests (incluidos
  los falsos positivos).
- **Decisión pendiente**: ninguna.

### A-13 — Constantes de contrato duplicadas y settings decorativos (C-10)

**Descripción**: modelo de embeddings en 3 sitios (`settings.embedder_model`
sin consumidor, default del adaptador, constante del script), dimensión 384
en 3 (ORM, script, DDL), LLM/URL/timeouts duplicados, variables
meteorológicas en 5 sitios.

- **Testigos**: CÓDIGO ✓ (`settings.py:15` vs `local_embedder.py:22` vs
  `ingest_knowledge.py:29-30`; `knowledge_base.py:17` vs `init.sql:20`;
  `settings.py:11-12` vs `opencode_go_llm.py:34-36`; `di.py:60-62` sin
  cablear el setting); DATOS/NEGOCIO ✗. Fuentes: C-10, C-05, C-06, C-07.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: evolución futura (cambios que "no cambian nada" o que
  rompen inserts por dimensión).
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar;
  unificación en modernización.
- **Decisión pendiente**: ninguna.

### A-14 — Embeddings: adaptador del runtime y script de ingesta independientes (C-07)

**Descripción**: la ingesta usa su propia instancia de `SentenceTransformer`
y SQL directo, sin pasar por el puerto `Embedder` ni por la configuración.

- **Testigos**: CÓDIGO ✓ (`ingest_knowledge.py:19-21,29,357-380,385-390` vs
  `local_embedder.py:12-30`); DATOS/NEGOCIO ✗. Fuentes: flujo §6e, C-07.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: mantenimiento (dos caminos que deben seguir alineados);
  riesgo de desalineación de embeddings si cambia el modelo o la librería.
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-15 — Sesiones de BD: dos fábricas y dos modelos transaccionales (C-08)

**Descripción**: `get_session_factory` (docstring "para inyección en
FastAPI", sin llamadores) frente a la `async_sessionmaker` propia del
adaptador RAG con transacción por operación.

- **Testigos**: CÓDIGO ✓ (`session.py:11-50`,
  `knowledge_base_adapter.py:27-37,42,58`, `di.py:53-58`); DATOS/NEGOCIO ✗.
  Fuentes: flujo §6f, memoria A6, C-08.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: código futuro de persistencia (p. ej. escribir en
  `forecasts`).
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna técnica.

### A-16 — Búsqueda vectorial definida dos veces (C-09)

**Descripción**: la búsqueda por similitud coseno existe en el adaptador
async (binding string, similitud validada [0,1]) y en el script de ingesta
(psycopg2 nativo, distancias crudas sin validación).

- **Testigos**: CÓDIGO ✓ (`knowledge_base_adapter.py:69-82` vs
  `ingest_knowledge.py:433-457`); DATOS/NEGOCIO ✗. Fuentes: C-09.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: evolución del esquema (dos consultas que pueden
  desincronizarse).
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-17 — El esquema de la base de datos tiene tres fuentes de verdad

**Descripción**: `init.sql`, Alembic y `db-sync` (create_all) definen el
mismo esquema por caminos independientes.

- **Testigos**: CÓDIGO ✓ (`init.sql:4-39`,
  `alembic/versions/821f93690b12_...py:20`, `Makefile:41-53`); DATOS/
  NEGOCIO ✗. Fuentes: R13, H6.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): **Alembic es la fuente de verdad**; `init.sql` solo para el primer arranque del contenedor; `db-sync` deprecado.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P7 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: entornos nuevos; migraciones futuras.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P7 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-18 — Cada conversación genera dos eventos que se pierden

**Descripción**: los eventos de dominio se recogen y descartan; y
`used_ml_prediction` es siempre `False` por discrepancia de etiquetas
(`weather_and_prediction` vs `ml_prediction`).

- **Testigos**: CÓDIGO ✓ (`agent/aggregate/__init__.py:37-38,56-57,105-114`
  (`:106` busca `"ml_prediction"`), `ask_agent/handler.py:134-135,173`);
  DATOS/NEGOCIO ✗. Fuentes: RN-27, mapa §4.2/§4.9, flujo §5, memoria A5.
- **Clasificación**: **BUG A SECAS**.
- **Dependientes**: auditoría/analítica futuras.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: ¿debían persistirse los eventos? Responsable: sin
  identificar.

### A-19 — La sesión de LLM se comparte entre todos los usuarios del proceso

**Descripción**: un único `x-opencode-session` por instancia singleton;
temperatura 0,7 y 1024 tokens fijos. (Regla protegida con incidente H3/W3:
el 400 MissingSessionID.)

- **Testigos**: CÓDIGO ✓ (`opencode_go_llm.py:31-44,69-76`, `di.py:64-69`;
  incidente narrado en `:43`); DATOS ✗ (el endpoint no se pudo llamar en
  esta fase); NEGOCIO ✗. Fuentes: RN-26, R14, W3, H3.
- **Clasificación**: **PENDIENTE** (parcialmente decidida): sesión **por proceso** aceptada; faltan copia del contrato y coste del endpoint.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P3 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: contrato con el proveedor; correlación posible de
  usuarios.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: copia del contrato y coste del LLM (acta P3, simulada; respondente compras/proveedor). Responsable: sin identificar.
### A-20 — Ciudades desconocidas se codifican a ceros por decisión documentada

**Descripción**: política de `handle_unknown="ignore"` + inyección del
nombre de ciudad; decisión documentada en docstring y entrenamiento. (Regla
protegida W4/H5; su consecuencia real es A-02.)

- **Testigos**: CÓDIGO ✓ (`train_model.py:178`,
  `local_predictor.py:173-176`); DATOS ✓ (categorías OneHot confirman el
  mecanismo activo); NEGOCIO ✗. Fuentes: RN-07, W4, H5.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): solo las **ciudades entrenadas están soportadas oficialmente**; el sistema puede responder para otras sin promesa de calidad. Información nueva del negocio: mercado prioritario **España**, Madrid ciudad de referencia, consultas en inglés secundarias (→ A-41).
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P8 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: Tokyo/São Paulo (A-02); ciudades nuevas.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: decidida en acta P8 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-21 — El wrapper del modelo es un contrato binario protegido

**Descripción**: `MultiOutputRegressorWithProgress` vive picklada como
`__main__` dentro de `model.pkl`; moverla inutiliza el activo; el predictor
reescribe `sys.modules["__main__"]` para cargarla. (Regla protegida con
incidente H4; advertencias W1/W2.)

- **Testigos**: CÓDIGO ✓ (`model_wrapper.py:1-8`, `local_predictor.py:21-31`,
  `train_model.py:26`); DATOS ✓ (el binario contiene las cadenas `__main__`
  y `MultiOutputRegressorWithProgress`; verificado por lectura de bytes
  2026-11-14); NEGOCIO ✗.
- **Clasificación**: **PENDIENTE** (parcialmente decidida): propietario del activo = **equipo de datos/ML**; falta el nombre concreto de la persona responsable.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P9 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: `models/model.pkl` (3,6 MB) y todo el subsistema de
  predicción.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual como
  restricción dura.
- **Decisión pendiente**: nombre del responsable de regenerar `model.pkl` (acta P9, simulada). Responsable: sin identificar.
### A-22 — La identidad del modelo es MD5 del binario + mtime del fichero

**Descripción**: la "versión" es un MD5 truncado y la fecha de entrenamiento
el mtime.

- **Testigos**: CÓDIGO ✓ (`local_predictor.py:153-163`); DATOS/NEGOCIO ✗.
  Fuentes: RN-12, R10, mapa §4.12.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): aceptada **provisionalmente**; en modernización el artefacto debe llevar versión y fecha reales dentro del propio fichero.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P10 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: trazabilidad de modelos; tabla `models` sin uso
  (`init.sql:32-39`).
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: decidida en acta P10 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-23 — Código de dominio completo sin consumidor

**Descripción**: agregado `Forecast` y sus eventos,
`WeatherInterpretationService`, `LocationQuery`, `MockLLM`, `NullLogger`,
`get_session`/`get_session_factory`, métodos de puerto sin llamador
(`get_model_version`, `get_historical_weather` en runtime, getters de
`PredictionResult`).

- **Testigos**: CÓDIGO ✓ (mapa §4.3-§4.6/§4.8 con líneas; verificación de
  llamadas 2026-11-14); DATOS ✗; NEGOCIO ✗. Fuentes: memoria A4-A8,
  RN métodos muertos.
- **Clasificación**: **ACCIDENTAL** (trabajo abandonado).
- **Dependientes**: nadie identificado (riesgo de confusión documental,
  A-26).
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar;
  baja en modernización previa caracterización.
- **Decisión pendiente**: ninguna (las tablas van en A-24).

### A-24 — Tablas `forecasts` y `models` creadas, mapeadas y sin escritor

**Descripción**: dos tablas de negocio sin ningún código que escriba o lea.

- **Testigos**: CÓDIGO ✓ (`init.sql:4-18,32-39`,
  `persistence/models/forecast.py:13`, `persistence/models/model.py:13`,
  único adaptador: `knowledge_base_adapter.py`); DATOS ✓ (verificación
  estructural de llamadas); NEGOCIO ✗. Fuentes: mapa §4.7, memoria A2/A3.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): tabla `forecasts` = **requisito pendiente** (se quiere histórico consultable de predicciones); tabla `models` = **descartada** (las métricas viajan en el artefacto).
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P11 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: esquema y migraciones futuras.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P11 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-25 — Higiene del repositorio: migración fantasma, cachés y vacíos

**Descripción**: bytecode de una migración borrada (`320b6a04018d_test_migration`),
`__pycache__` commiteados fuera de la raíz, `README.md` y `docs/` vacíos.

- **Testigos**: CÓDIGO/DATOS ✓ (`alembic/versions/__pycache__/320b6a04018d_test_migration.cpython-38.pyc`
  sin `.py` correspondiente; `scripts/__pycache__/`; `.gitignore:2`; README
  0 bytes; docs vacío); NEGOCIO ✗. Fuentes: mapa §4.15-§4.17, memoria A1/A11.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: nadie identificado.
- **Tratamiento**: sin acordar; propuesta: limpieza en modernización.
- **Decisión pendiente**: ninguna.

### A-26 — Docstrings prometen implementaciones y mejoras inexistentes

**Descripción**: puertos con `MeteostatAdapter`, `MockWeatherProvider`,
`RemoteEmbedder`, `RemotePredictor`, `CachedFeatureExtractor`,
`ChromaDBAdapter`, `InMemoryVectorStore`; clasificador que promete "en
producción un modelo NLP".

- **Testigos**: CÓDIGO ✓ (`weather/repository/__init__.py:69`,
  `agent/repository/embedder.py:10`, `agent/repository/vector_store.py:12`,
  `ml/repository/__init__.py:15,67`, `query_intent.py:154-155`); DATOS/
  NEGOCIO ✗. Fuentes: R16, memoria A7/A10.
- **Clasificación**: **ACCIDENTAL** (deuda documental).
- **Dependientes**: desarrolladores/agentes futuros.
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-27 — Validación de entrada vacía en dos capas con códigos distintos (C-03)

**Descripción**: pregunta vacía → 422 (Pydantic) o 400 (dominio) según
dónde falle; `"   "` pasa la primera y falla la segunda.

- **Testigos**: CÓDIGO ✓ (`chat.py:27` vs `command.py:18-21` +
  `chat.py:73-78`); DATOS/NEGOCIO ✗. Fuentes: flujo §6d, C-03.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: clientes que distingan códigos de error.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: ninguna.

### A-28 — Capa HTTP duplicada y asimétrica entre rutas (C-04)

**Descripción**: `/chat` y `/predict` duplican el mapeo de errores y
difieren en el manejador genérico (500 con detalle vs 500 por defecto) y en
el logging.

- **Testigos**: CÓDIGO ✓ (`chat.py:67-84` vs `predict.py:84-99`); DATOS/
  NEGOCIO ✗. Fuentes: flujo §6c, C-04.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: clientes de ambos endpoints; observabilidad.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: ninguna.

### A-29 — Doble parsing de la misma frase (intención y ciudad)

**Descripción**: intención (palabras clave) y ciudad (regex) analizan la
misma pregunta con lógicas independientes.

- **Testigos**: CÓDIGO ✓ (`query_intent.py:151-179` vs
  `ask_agent/handler.py:83-93`); DATOS/NEGOCIO ✗. Fuentes: flujo §6g,
  RN-19/22.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: comportamiento ante preguntas mixtas.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: ninguna.

### A-30 — Preguntas históricas respondidas con tiempo actual

**Descripción**: la intención HISTORICAL no tiene camino a datos históricos
en runtime.

- **Testigos**: CÓDIGO ✓ (`query_intent.py:99,141-147`,
  `ask_agent/handler.py:151-152`, `open_meteo_adapter.py:125-171` sin
  llamador); DATOS/NEGOCIO ✗. Fuentes: RN-21, flujo caso D.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): aceptable **de momento**; el histórico real entra en la lista de deseos del producto (feature futura con datos de archivo).
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P12 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: usuarios con preguntas históricas.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P12 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-31 — El RAG se consulta siempre y sin umbral de calidad

**Descripción**: toda pregunta recupera los 3 documentos más similares sin
puntuación mínima.

- **Testigos**: CÓDIGO ✓ (`ask_agent/handler.py:118-121,192`,
  `knowledge_base_adapter.py:69-82`); DATOS/NEGOCIO ✗. Fuentes: RN-20/23,
  mapa §4.13.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): **se quiere umbral mínimo** de similitud (no meter documentos poco relacionados); hasta implementarlo, el comportamiento actual queda aceptado a sabiendas.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P13 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: coste y calidad de cada respuesta.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: decidida en acta P13 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-32 — Privacidad: el prompt completo del usuario va a los logs

**Descripción**: nivel INFO registra prompt completo, resumen meteorológico
y contenido RAG; `DEBUG=true` añade todas las SQL.

- **Testigos**: CÓDIGO ✓ (`ask_agent/handler.py:127,170,196-202`,
  `session.py:21`, `settings.py:16`); DATOS/NEGOCIO ✗. Fuentes: R9/R18.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): logs **internos y de uso operativo**, sin política externa aplicable hoy; en modernización el texto completo del usuario pasa a nivel DEBUG.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P14 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: retención de logs; cumplimiento si aplica.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P14 (simulada). Responsable: sin identificar (ratificación real pendiente).
### A-33 — Similitud RAG sin acotar antes de validar

**Descripción**: `1 - (embedding <=> …)::float` puede salir de [0,1] por
redondeo y el value object lo rechaza a mitad de petición (400).

- **Testigos**: CÓDIGO ✓ (`knowledge_base_adapter.py:74,95`,
  `retrieved_document.py:46-49`, `chat.py:73-78`); DATOS/NEGOCIO ✗.
  Fuentes: R15.
- **Clasificación**: **BUG A SECAS** (latente, baja probabilidad).
- **Dependientes**: disponibilidad del chat en casos extremos.
- **Tratamiento**: sin acordar; propuesta: caracterizar y corregir en
  modernización.
- **Decisión pendiente**: ninguna.

### A-34 — SQL con interpolación de nombre de tabla

**Descripción**: FROM construido por f-string; hoy el valor es fijo, el
patrón admite inyección si se externaliza.

- **Testigos**: CÓDIGO ✓ (`knowledge_base_adapter.py:27-31,72-78`,
  `di.py:55-58`); DATOS/NEGOCIO ✗. Fuentes: R12.
- **Clasificación**: **ACCIDENTAL** (riesgo latente).
- **Dependientes**: nadie identificado.
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-35 — Carrera en la carga perezosa del modelo y doble copia por handler

**Descripción**: peticiones concurrentes pueden disparar dos `load_model`;
`AskAgentHandler` y `PredictHandler` mantienen copias propias del modelo.

- **Testigos**: CÓDIGO ✓ (`ask_agent/handler.py:64-68`,
  `predict/handler.py:44-48`, `di.py:72-90`); DATOS/NEGOCIO ✗. Fuentes: R7.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: memoria y latencia del primer arranque.
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-36 — Python 3.8 EOL, versiones sin fijar y auditoría de CVEs sin hacer

**Descripción**: runtime 3.8.10 (EOL), dependencias solo con `>=`, revisión
de avisos de seguridad pendiente.

- **Testigos**: CÓDIGO ✓ (`requirements.txt:1-33`, `pyproject.toml:60,66`);
  DATOS ✓ (`venv/bin/python --version` = 3.8.10; pip list 2026-11-14:
  scikit-learn 1.3.2, pandas 2.0.3); NEGOCIO ✗. Fuentes: R5/R19.
- **Clasificación**: **PENDIENTE → INTENCIONAL** (provisional): auditoría de dependencias **trimestral por el equipo de desarrollo**; **aprobada** la migración fuera de Python 3.8 en modernización.
  Testigo NEGOCIO: `acta-entrevista-negocio.md`, P15 (respondente **simulado**, sin nombre real, 2026-11-14; ratificación real pendiente).
- **Dependientes**: parches de seguridad; reproducibilidad.
- **Tratamiento**: sin acordar.
- **Decisión pendiente**: decidida en acta P15 (simulada); queda pendiente la primera auditoría real. Responsable: sin identificar (ratificación real pendiente).
### A-37 — Tests anunciados e inexistentes, con versiones contradictorias

**Descripción**: pytest/respx declarados y configurados sin directorio
`tests/`; `requirements.txt` (pytest>=7.4) y `pyproject.toml` (pytest>=8.3)
en desacuerdo.

- **Testigos**: CÓDIGO ✓ (`requirements.txt:28-33`, `pyproject.toml:29-32,56-61`,
  ausencia de `tests/`); DATOS/NEGOCIO ✗. Fuentes: R17, mapa §4.14, memoria
  A8/A9.
- **Clasificación**: **ACCIDENTAL** (bloquea la fase de caracterización).
- **Dependientes**: la propia fase de tests; CI.
- **Tratamiento**: sin acordar; propuesta: resolver versiones al crear
  `tests/` (sin dependencias nuevas).
- **Decisión pendiente**: ninguna técnica.

### A-38 — Variables calculadas en runtime y descartadas por el modelo

**Descripción**: el extractor genera lags de 8 variables pero el modelo solo
consume 6; los lags de dirección del viento y punto de rocío se calculan y
se tiran. (Corrección de RN-09 por datos.)

- **Testigos**: CÓDIGO ✓ (`feature_extractor.py:63-72`,
  `predict/handler.py:108-115`, `train_model.py:48` definida y sin uso);
  DATOS ✓ (`feature_columns` del artefacto sin dew/wind_direction); NEGOCIO
  ✗. Fuentes: RN-09 corregida, mapa §4.1.
- **Clasificación**: **ACCIDENTAL** (cálculo muerto).
- **Dependientes**: nadie identificado (coste y confusión).
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-39 — Sin redondeos en ninguna salida de negocio

**Descripción**: predicciones y resúmenes se entregan con todos los
decimales; no hay política de redondeo.

- **Testigos**: CÓDIGO ✓ (`ask_agent/handler.py:248-254`, `predict.py:41-46`);
  DATOS/NEGOCIO ✗. Fuentes: RN-13.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: presentación al usuario final.
- **Tratamiento**: sin acordar; propuesta: especificar tal cual.
- **Decisión pendiente**: ¿política de redondeo en modernización?
  Responsable: sin identificar.

### A-40 — R² publicado como 0 cuando la variable no varía

**Descripción**: si una variable es constante en test, su R² se reporta
como 0 en lugar de "no calculable".

- **Testigos**: CÓDIGO ✓ (`train_model.py:227-228`); DATOS/NEGOCIO ✗.
  Fuentes: RN-18.
- **Clasificación**: **ACCIDENTAL**.
- **Dependientes**: métricas publicadas del entrenamiento.
- **Tratamiento**: sin acordar; propuesta: documentar sin especificar.
- **Decisión pendiente**: ninguna.

### A-41 — El mercado prioritario declarado (España/Madrid) no está reflejado en el sistema

**Descripción**: el negocio declara España como mercado prioritario y Madrid
como ciudad de referencia (acta P8), pero el dataset es global (10 ciudades,
`download_historical.py:22-34`) y la extracción de ciudad solo cubre
patrones "in/at/for/en" con inicial mayúscula (`ask_agent/handler.py:83-93`),
sin soporte específico del mercado declarado.

- **Testigos**: CÓDIGO ✓ (`download_historical.py:22-34`,
  `ask_agent/handler.py:83-93`); DATOS ✗; NEGOCIO ✓ (acta P8, **simulado**,
  2026-11-14; ratificación real pendiente). Entrada nueva generada por la
  entrevista, no presente en documentos previos.
- **Clasificación**: **PENDIENTE** — pregunta que la desbloquea: *¿se alinea
  el dataset (ciudades españolas prioritarias) y el idioma de consulta con
  el mercado declarado dentro del reentrenamiento de A-01?*
- **Dependientes**: calidad de predicciones para el mercado prioritario;
  contenido de `data/historical_weather.csv`; `OneHotEncoder` del artefacto.
- **Tratamiento**: sin acordar; propuesta: incluir la alineación de dataset
  en el paquete de reentrenamiento de A-01 (no retroactiva).
- **Decisión pendiente**: alcance del reentrenamiento respecto al mercado.
  Responsable: sin identificar.

---

## Cambios de clasificación tras la ronda de entrevista (acta 2026-11-14)

Registro explícito de transiciones (nada sobrescrito en silencio). Fuente:
`acta-entrevista-negocio.md` (entrevista **simulada**; respondente sin
nombre real).

- **PENDIENTE → INTENCIONAL (provisional)**: A-05 (auth), A-08, A-09, A-17,
  A-20, A-22, A-24, A-30, A-31, A-32, A-36.
- **Transición parcial dentro de la entrada**: A-05 (la exposición del texto
  de excepciones baja a BUG A SECAS), A-24 (split forecasts/models).
- **Siguen PENDIENTE**: A-19, A-21 (parcialmente decididas), **A-41 (nueva)**.
- **Nota constitucional**: el testigo NEGOCIO del acta es **simulado**; no
  computa como testigo válido hasta su ratificación por una persona real con
  nombre y fecha (Principio II). Las marcas INTENCIONAL (provisional) lo
  reflejan.

---

## Tabla resumen

| ID | Clasificación | Tratamiento (propuesto, sin acordar) | Decisión pendiente |
|---|---|---|---|
| A-01 | BUG HISTÓRICO CON DEPENDIENTES | corregir con reentrenamiento (no retroactiva); especificar tal cual mientras | estrategia de split/reentrenamiento |
| A-02 | BUG HISTÓRICO CON DEPENDIENTES | documentar calidad desconocida; corregir con A-01 | avisar soporte de ciudades no entrenadas |
| A-03 | BUG A SECAS | caracterizar y corregir en modernización | — |
| A-04 | BUG HISTÓRICO CON DEPENDIENTES | especificar tal cual; corregir con reentrenamiento | aceptar aproximación de lags |
| A-05 | INTENCIONAL* (auth) + BUG A SECAS (detalle) | detalle de error en modernización (acta P4) | ratificación real |
| A-06 | BUG A SECAS | especificar tal cual; unificar en modernización | — |
| A-07 | BUG A SECAS | especificar tal cual; validar en modernización | — |
| A-08 | INTENCIONAL* | especificar tal cual (acta P5) | ratificación real |
| A-09 | INTENCIONAL* | restricción: solo local + checklist (acta P6) | ratificación real |
| A-10 | BUG A SECAS | corregir en modernización | — |
| A-11 | BUG A SECAS | declarar dependencias existentes | — |
| A-12 | BUG A SECAS | caracterizar antes de tocar | — |
| A-13 | ACCIDENTAL | documentar sin especificar | — |
| A-14 | ACCIDENTAL | documentar sin especificar | — |
| A-15 | ACCIDENTAL | documentar sin especificar | — |
| A-16 | ACCIDENTAL | documentar sin especificar | — |
| A-17 | INTENCIONAL* | Alembic fuente de verdad; db-sync deprecado (acta P7) | ratificación real |
| A-18 | BUG A SECAS | especificar tal cual | ¿persistir eventos? |
| A-19 | PENDIENTE | especificar tal cual (sesión por proceso aceptada, acta P3) | copia del contrato y coste del LLM |
| A-20 | INTENCIONAL* | solo ciudades entrenadas soportadas (acta P8) | ratificación real |
| A-21 | PENDIENTE | restricción dura (propietario: equipo datos/ML, acta P9) | nombre del responsable |
| A-22 | INTENCIONAL* | provisional; versión real en modernización (acta P10) | ratificación real |
| A-23 | ACCIDENTAL | documentar sin especificar | — |
| A-24 | INTENCIONAL* | forecasts a spec futura; models retirada (acta P11) | ratificación real |
| A-25 | ACCIDENTAL | limpieza en modernización | — |
| A-26 | ACCIDENTAL | documentar sin especificar | — |
| A-27 | ACCIDENTAL | especificar tal cual | — |
| A-28 | ACCIDENTAL | especificar tal cual | — |
| A-29 | ACCIDENTAL | especificar tal cual | — |
| A-30 | INTENCIONAL* | aceptado de momento; histórico en deseos (acta P12) | ratificación real |
| A-31 | INTENCIONAL* | tal cual + umbral en modernización (acta P13) | ratificación real |
| A-32 | INTENCIONAL* | logs internos; texto a DEBUG (acta P14) | ratificación real |
| A-33 | BUG A SECAS | caracterizar y corregir en modernización | — |
| A-34 | ACCIDENTAL | documentar sin especificar | — |
| A-35 | ACCIDENTAL | documentar sin especificar | — |
| A-36 | INTENCIONAL* | auditoría trimestral + migrar 3.8 (acta P15) | primera auditoría real |
| A-37 | ACCIDENTAL | resolver versiones al crear `tests/` | — |
| A-38 | ACCIDENTAL | documentar sin especificar | — |
| A-39 | ACCIDENTAL | especificar tal cual | ¿política de redondeo? |
| A-40 | ACCIDENTAL | documentar sin especificar | — |
| A-41 | PENDIENTE | alinear dataset con el mercado en el reentrenamiento de A-01 | alcance del reentrenamiento (España/Madrid) |

## Lista de clasificaciones PENDIENTES (agenda con el negocio)

**Estado tras la ronda simulada (acta 2026-11-14): 3 entradas.** Las
decisiones del acta son **propuestas** (respondente simulado); la
ratificación real con nombre y fecha es requisito para vaciar la lista:

1. **A-19** — Copia del contrato y coste del endpoint OpenCode Go (la
   sesión por proceso ya está aceptada en acta P3). Respondente: compras/
   proveedor.
2. **A-21** — Nombre concreto del responsable de regenerar `model.pkl` (el
   rol sí está decidido: equipo de datos/ML, acta P9).
3. **A-41** — ¿Se alinea el dataset (ciudades españolas prioritarias) y el
   idioma de consulta con el mercado declarado, dentro del reentrenamiento
   de A-01?

Fuera de la lista (clasificación cerrada, decisión abierta): **A-39**
(política de redondeo, sin respuesta concluyente, acta §4).

Además: **todas** las decisiones del acta requieren ratificación real
(nombre y fecha) antes de que las clasificaciones INTENCIONAL computen
definitivamente.

**Estado**: la lista PENDIENTE no está vacía → es la agenda de la siguiente
conversación con el negocio; no se procede a specs formales hasta vaciarla
con testimonios reales (nombre y fecha), conforme a la regla de dos de tres
testigos.
