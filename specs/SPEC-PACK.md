# SPEC-PACK — Paquete de especificación del sistema weather-agent

**Fecha**: 2026-11-14 · **Versión**: 1.0 · **Estado**: pendiente de aprobación del negocio

Documento de entrada única al paquete. Recoge en un solo lugar el resumen
para dirección, el inventario de riesgos priorizado, el índice comentado
de la documentación y el estado de la red de seguridad (tests).

**Aviso metodológico**: todas las decisiones de negocio citadas proceden
de una entrevista **simulada** (`specs/000-reconocimiento/acta-entrevista-negocio.md`,
rondas 1 y 2, 2026-11-14). Ninguna decisión computa como ratificada hasta
que una persona identificada la confirme con su nombre y fecha.

---

## 1. Resumen ejecutivo para el gerente

### Qué se ha hecho

Se ha documentado por completo un sistema que funcionaba sin documentación
ni tests: un asistente conversacional del tiempo con predicción
meteorológica automática. El trabajo se hizo **sin tocar el código**: se
describió lo que el sistema ya hace, se congeló ese comportamiento con una
red de 190 tests automáticos y se redactaron cinco especificaciones
formales que servirán de contrato para cualquier modernización futura.
Nada del sistema ha cambiado; ahora es conocido, medido y protegido.

### Qué se ha descubierto (lo que el gerente debería saber)

1. **El modelo nunca aprendió de dos de sus diez ciudades.** La "prueba de
   calidad" del modelo (un 37 % que hoy podría interpretarse como
   "acierto") no mide eso: mide la diferencia entre ciudades, porque la
   prueba estaba construida con Tokyo y São Paulo, ciudades que el modelo
   nunca vio. Tokyo y São Paulo reciben predicciones de un modelo que las
   ignora. **Recomendación**: reentrenar el modelo correctamente antes de
   ampliar el servicio (decisión ya tomada en simulación).
2. **El chat responde con predicciones partiendo de un estado
   meteorológico vacío.** Con las mismas condiciones reales (18,5 °C en
   Madrid), la página de datos dice 18,2 °C a 6 horas y el chat dice 6,0 °C.
   El motivo: dos módulos nombran los datos de forma distinta y el chat se
   queda con ceros. **Recomendación**: corregirlo en la modernización, no
   antes (cambiarlo ahora alteraría un comportamiento que alguien podría
   estar usando).
3. **El chat no reconoce ciudades con ñ o ã.** Si un usuario pregunta por
   São Paulo o A Coruña, el sistema no identifica la ciudad y responde sin
   dato meteorológico, aunque São Paulo sí está en el dataset. **Recomendación**:
   corrección barata y de alto valor percibido; incluir en el mismo paquete
   de modernización.
4. **La predicción "a 6 horas" cambia según lo que se pida.** Pedir solo 6
   horas da 4,3 °C; pedir 6, 12 y 24 horas da 18,2 °C, con los mismos datos.
   Nadie lo había detectado porque casi todos usan la opción por defecto.
   **Recomendación**: mantenerlo congelado y decidir en la modernización.

### Qué protección se ha instalado

Una red de **190 tests automáticos** que fotografían el sistema tal como
es hoy: si alguien cambia cualquier comportamiento —aunque sea por
accidente— la red salta y avisa. Incluye una "foto oficial" (golden master)
de las doce situaciones típicas de predicción, con todos sus decimales.

### Qué tiene pendiente de decidir el negocio

Todas las decisiones están tomadas **en simulación** y esperan ratificación
por una persona responsable con nombre y fecha. Las clave: reentrenar el
modelo (sí), corregir el chat y las ciudades con ñ (sí, en modernización),
mantener el servicio sin redondeos como contrato (sí), horizontes oficiales
de 6/12/24 horas (sí). **Recomendación**: una sesión única de ratificación
de ~90 minutos con producto, TI y datos/ML usando las actas como guion.

---

## 2. Inventario de riesgos priorizado

Ordenado por impacto de negocio × probabilidad. Fuente:
`specs/000-reconocimiento/registro-riesgos.md` (R1-R21) y
`registro-de-anomalias.md` (A-01..A-43). Solo se listan los de mayor
relevancia para decidir la implementación; el detalle completo está en los
registros.

| # | Riesgo | Impacto en una frase | Recomendación para continuar |
|---|---|---|---|
| 1 | **A-01/A-02** Split de entrenamiento por ciudades; Tokyo/São Paulo sin aprender; métrica 0,37 interpretable como fiabilidad | Decisiones de negocio tomadas sobre una calidad que no es la real; calidad desconocida para 2 de 10 ciudades | Reentrenar en modernización (acta P1/§8); mientras tanto, prohibido citar el 0,37 (R21) y documentar ciudades no soportadas |
| 2 | **A-03/C-01** El chat predice desde condiciones nulas | Respuestas conversacionales con divergencias de hasta ~12 °C frente a `/predict` | Congelado; corregir en modernización alineando a la convención Open-Meteo (acta P16) |
| 3 | **R20** Coste del LLM sin control ni registro | Partida operativa que puede crecer sin visibilidad | Antes de ampliar uso: medir coste por llamada y comparar contra el cap (acta P3/§8) |
| 4 | **A-05** Sin autenticación y 500 de `/chat` con texto interno | Cualquier cliente de la red ve detalles internos del sistema | Auth aceptada por postura interna (acta P4); respuesta genérica de error en modernización |
| 5 | **A-42** Ciudades con ñ/ã no reconocidas en el chat | Usuarios de ciudades españolas con ñ/ã reciben respuesta sin dato | Corregir en modernización junto con la ampliación de idioma (acta §8) |
| 6 | **A-43** La predicción depende de los horizontes pedidos | Un cliente que pida solo 6 h recibe valores distintos a los "oficiales" | Congelado; decidir en modernización si se valida el contrato de horizontes |
| 7 | **A-09** Credenciales `weather`/`weather` por defecto | Un despliegue sin override deja credenciales conocidas en producción | Checklist de despliegue obligatoria (acta P6/H13) |
| 8 | **A-10** La recarga del RAG puede dejar la base vacía | Tras un fallo a medias, el chat responde sin contexto hasta recargar | Transacción única en modernización; operar con procedimiento documentado |
| 9 | **A-36** Python 3.8 sin soporte y dependencias sin auditar | Sin parches de seguridad ni instalaciones reproducibles | Migración de runtime aprobada (acta P15); auditoría trimestral |
| 10 | **A-21** El modelo depende de una clase picklada como `__main__` | Cualquier reorganización de código inutiliza el activo de 3,6 MB | Restricción dura: solo el equipo de datos/ML regenera el modelo (acta §8) |

## 3. Índice comentado del paquete

| Documento | Qué contiene | Cuándo consultarlo |
|---|---|---|
| `specs/000-reconocimiento/mapa-sistema.md` | Mapa completo del sistema: módulos, dependencias, criticidad, tecnologías reales y "zonas oscuras" | Para orientarse: qué existe y qué pesa |
| `specs/000-reconocimiento/reglas-de-negocio.md` | Las 28 reglas de negocio con ejemplos numéricos y clasificación (RN-01..RN-28; RN-28 refutada por datos) | Para saber qué hace el sistema y por qué |
| `specs/000-reconocimiento/contradiccion-01..10-*.md` | Diez conceptos implementados dos veces, con divergencias cuantificadas (C-01..C-10) | Antes de tocar cualquier cálculo o validación |
| `specs/000-reconocimiento/registro-de-anomalias.md` | Registro único A-01..A-43 con testigos, clasificación, tratamiento y decisiones; lista PENDIENTE vacía | Antes de cambiar cualquier comportamiento |
| `specs/000-reconocimiento/registro-riesgos.md` | Riesgos R1-R21 con impacto y probabilidad | Para priorizar la modernización |
| `specs/000-reconocimiento/memoria-historica.md` | Cronología H1-H14, advertencias "no tocar" W1-W4 y trabajos abandonados | Para no repetir incidentes (H3/H4 son incidentes reales) |
| `specs/000-reconocimiento/acta-entrevista-negocio.md` | Entrevista de negocio simulada: 18 preguntas (P1-P18) + ronda 2 (§8); decisiones pendientes de ratificación real | Para la sesión de ratificación con el negocio |
| `specs/000-reconocimiento/propuesta-particion-specs.md` | Partición en 5 dominios con trazabilidad completa y descripciones de entrada | Para entender por qué existen exactamente estas 5 specs |
| `specs/001-datos-meteorologicos/spec.md` | SPEC-01: geocodificación, magnitudes y límites físicos (RN-01..04) | Contrato del dato meteorológico |
| `specs/002-prediccion-numerica/spec.md` | SPEC-02: contrato de `/predict`, horizontes, alineación, identidad del modelo (RN-05..13) | Contrato numérico del producto |
| `specs/003-agente-conversacional/spec.md` | SPEC-03: `/chat`, intención, ciudad, RAG, prompt, LLM, eventos (RN-10, 19-27) | Contrato conversacional |
| `specs/004-entrenamiento-artefacto-ml/spec.md` | SPEC-04: dataset, partición, lags, constantes, artefacto protegido (RN-12, 14-18) | Contrato del activo de datos/ML |
| `specs/005-plataforma-operacion/spec.md` | SPEC-05: configuración, errores HTTP, persistencia, logs, dependencias, higiene | Contrato de operación y plataforma |
| `tests/` (suite de caracterización) | 190 tests que congelan el comportamiento actual + golden master de 12 casos | Ver instrucciones abajo |

**Glosario mínimo** (términos de negocio usados en el paquete):

- **Horizonte**: dentro de cuántas horas se predice (oficiales: 6, 12 y 24).
- **Lag**: el valor de una variable "h horas antes", entrada del modelo.
- **OneHot**: la lista de ciudades que el modelo "conoce" por su nombre
  (8 ciudades; las demás entran como "desconocida").
- **RAG**: la base de conocimiento meteorológica que alimenta las
  respuestas del chat.
- **Golden master**: la foto oficial de las salidas del sistema, contra la
  que se compara cada cambio.
- **test_score 0,37**: métrica interna del modelo ENTRE ciudades; no es la
  fiabilidad del servicio (prohibido citarla como tal, R21).

## 4. Estado de la red de seguridad

### Congelado (cualquier cambio salta en `make test`)

- **Magnitudes y límites físicos** (RN-04): las 8 magnitudes con los tres
  puntos por lado (`tests/test_rn04_value_objects.py`).
- **Contrato de `/predict`**: horizontes, nombres de salida, alineación,
  lags a valor actual, ciudades OneHot y fuera, dependencia de horizontes
  pedidos, identidad del modelo (`tests/test_rn05_rn06_rn07_predictor.py`,
  `tests/test_rn07_rn08_rn09_feature_extractor.py`).
- **Golden master de 12 casos** del flujo `/predict` con todos los
  decimales (`tests/golden_master/master.json`; regeneración solo con
  decisión de negocio documentada, ver `LEEME.md` junto al master).
- **Agente conversacional (lógica)**: intención por subcadenas, extracción
  de ciudad (incluido el fallo con ñ/ã), ciclo de sesión, prompt literal,
  eventos perdidos, la divergencia chat-vs-predict
  (`tests/test_rn19_query_intent.py`, `tests/test_rn22_city_extraction.py`,
  `tests/test_rn24_rn27_chat_session.py`, `tests/test_rn25_rn13_prompt_summary.py`,
  `tests/test_c01_conversion_duplicada.py`).
- **Contratos transversales**: validación de entrada en dos capas, asimetría
  de errores HTTP entre `/chat` y `/predict`, constantes duplicadas, la
  semántica de entrenamiento (lags por filas, targets, colas) y las
  constantes del entrenamiento (`tests/test_c02..c05`).

### NO congelado (primera tarea de la siguiente fase)

1. **Rutas HTTP de extremo a extremo**: los tests cubren los manejadores
   con dependencias sustituidas, pero no el arranque real de la aplicación
   (`main.py`), el cableado del contenedor (`di.py`) ni la página
   `chat.html`. **Queda señalada como primera tarea de la siguiente fase**:
   subir el servicio con el modelo real y congelar el ciclo
   petición→respuesta completo de `/chat` y `/predict`.
2. **Remesa end-to-end con infraestructura**: Open-Meteo (geocoding y
   forecast), el LLM OpenCode Go (incluido el contrato de sesión A-19) y
   PostgreSQL/pgvector (RAG, C-09) están documentados con evidencia pero
   fuera de la red: requieren red/BD. Congelarlos exige un entorno de
   integración con grabadora de respuestas.
3. **Entrenamiento completo y scripts offline**: solo las funciones puras
   están congeladas; reentrenar de bout en bout está fuera (intencional:
   es la decisión de modernización).
4. **Ingesta del RAG y migraciones**: `ingest_knowledge.py` y Alembic no
   tienen red de protección.

### Instrucciones de ejecución de la suite

Este proyecto es **Python** (no hay `npm` ni `package.json` de aplicación;
el equivalente a `npm test` es):

```bash
make install                 # una vez: crea venv e instala dependencias
make test                    # ejecuta la suite: PYTHONPATH=. venv/bin/pytest
make test-coverage           # la misma suite con informe de cobertura
make golden-master           # regenera la foto oficial (SOLO con decisión de negocio documentada)
```

Estado actual: **190 tests en verde**; linter, formateador y tipos limpios
(`make check`).

---

*El paquete queda listo para la sesión de ratificación del negocio y, con
ella aprobada, para la fase de modernización dirigida por estas specs.*
