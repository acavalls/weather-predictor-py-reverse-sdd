# Acta de entrevista de negocio — reconocimiento weather-agent

**Fecha**: 2026-11-14
**Consultor**: agente de código (opencode)
**Respondente**: negocio (ver aviso de simulación)
**Aviso de simulación (obligatorio)**: esta acta recoge una **entrevista
simulada**: las respuestas las ha generado el propio consultor "con la
respuesta de mayor lógica", a petición del usuario, sin intervención de una
persona real del negocio. Conforme a la constitución (Principio II), un
testigo NEGOCIO exige **nombre y fecha reales**; hasta que una persona real
ratifique cada decisión con su nombre, las decisiones aquí recogidas quedan
como **decisiones propuestas** y las clasificaciones selladas como
INTENCIONAL siguen siendo **provisionales**. Nada de esto habilita la fase
de especificación formal: la lista de PENDIENTES solo quedará vacía con la
ratificación real.

---

## 1. Notas del consultor (turno a turno, ordenadas por impacto económico)

### P1 — Reentrenamiento del modelo (A-01, A-02) → Responsable del producto de predicción
**Pregunta**: ¿reentrenar con split correcto (10 ciudades, métrica realista), mantener y avisar de ciudades no soportadas, o necesita más info?
**Respuesta simulada**: **(a) Reentrenar**, pero en la fase de modernización, no ahora. El modelo actual sigue en servicio hasta entonces.
**Condiciones sueltas**: el reentrenamiento debe ir acompañado de un informe de métricas "que entienda negocio"; mientras tanto, prohibido citar el 0,37 como fiabilidad del producto (es la medida entre ciudades, no la del servicio).

### P2 — Aproximación de lags (A-04) → Responsable del producto de predicción
**Pregunta**: ¿aceptar que la inferencia use el valor actual como "valor de hace h horas"?
**Respuesta simulada**: aceptarla **como provisional**; alinearlo con la semántica del entrenamiento en el mismo paquete de modernización del reentrenamiento.
**Condición**: si se reentrena (P1), la semántica de lags debe quedar definida antes de entrenar, no después.

### P3 — Contrato y coste del LLM (A-19) → Responsable de compras/proveedor
**Pregunta**: ¿sesión por proceso o por usuario? ¿Contrato del endpoint OpenCode Go?
**Respuesta simulada**: sesión **por proceso** es aceptable (es interno); el contrato existe pero no está a mano: **sin respuesta concluyente** hasta aportar copia del contrato y coste por token. Presupuesto: el coste mensual del LLM no debe crecer por encima del doble del gasto actual.
**Condición nueva**: toda llamada al LLM debe quedar registrada en el presupuesto de operación mensual.

### P4 — Postura de seguridad (A-05) → Responsable de TI/infraestructura
**Pregunta**: ¿servicio interno en red de confianza? ¿Se acepta exponer el texto de excepciones?
**Respuesta simulada**: servicio **interno** (red de confianza): la ausencia de autenticación es aceptada tal cual. Exponer el texto de excepciones **no** es aceptado: corregir en modernización (respuesta genérica + detalle solo en logs).
**Efecto**: la ausencia de auth queda INTENCIONAL; el detalle de excepciones queda como defecto a corregir.

### P5 — Horizontes de negocio (A-08, A-07) → Responsable del producto de predicción
**Pregunta**: ¿qué horizontes son oficiales? ¿Hay consumidor para 48/72/168?
**Respuesta simulada**: horizontes oficiales **6/12/24 horas**; 48/72/168 **sin consumidor identificado**: quedan descartados del contrato de API (pueden seguir entrenándose si es barato, pero no se exponen).
**Condición**: si negocio pide más horizontes en el futuro, será una decisión nueva con impacto en reentrenamiento.

### P6 — Credenciales por defecto (A-09) → Responsable de TI/infraestructura
**Pregunta**: ¿aceptadas `weather`/`weather` como valores por defecto?
**Respuesta simulada**: aceptadas **solo para entorno local**; prohibido desplegar en producción sin sobreescribirlas; añadir a la checklist de despliegue.

### P7 — Fuente de verdad del esquema (A-17) → Responsable técnico
**Pregunta**: ¿init.sql o Alembic?
**Respuesta simulada**: **Alembic es la fuente de verdad** a partir de ahora; `init.sql` solo para el primer arranque del contenedor; `db-sync` se considera deprecado.

### P8 — Ciudades fuera del dataset (A-20) → Responsable del producto
**Pregunta**: ¿es política oficial predecir para ciudades que el modelo no conoce?
**Respuesta simulada**: política: **solo las ciudades entrenadas están soportadas oficialmente**; el sistema puede responder para otras, sin promesa de calidad y sin anunciarlo como soporte.
**Información nueva**: el mercado prioritario es **España**; Madrid es la ciudad de referencia; consultas en inglés son secundarias.

### P9 — Propiedad del modelo (A-21) → Responsable técnico
**Pregunta**: ¿quién regenera `model.pkl` si hay que tocar la clase envoltorio?
**Respuesta simulada**: el **equipo de datos/ML** es el propietario; cualquier cambio del wrapper exige reentrenamiento coordinado con ellos. Pendiente designar responsable concreto con nombre (requisito de la constitución).

### P10 — Identidad del modelo (A-22) → Responsable técnico
**Pregunta**: ¿se acepta versión=MD5 y fecha=mtime como oficial?
**Respuesta simulada**: aceptada **provisionalmente**; en modernización el artefacto debe llevar versión y fecha reales dentro del propio fichero.

### P11 — Tablas `forecasts` y `models` (A-24) → Responsable del producto
**Pregunta**: ¿requisito pendiente o descartadas?
**Respuesta simulada**: `forecasts` (historial de predicciones) es **requisito pendiente**: se quiere histórico consultable; `models` queda **descartada** (las métricas viajan en el artefacto).

### P12 — Preguntas históricas (A-30) → Responsable del producto
**Pregunta**: ¿es aceptable responder preguntas históricas con el tiempo actual?
**Respuesta simulada**: aceptable **de momento**, pero el producto debe añadir el "histórico real" a la lista de deseos (feature futura con datos de archivo).

### P13 — Umbral del RAG (A-31) → Responsable del producto
**Pregunta**: ¿se exige un parecido mínimo para que un documento entre en el contexto?
**Respuesta simulada**: **sí se quiere un umbral** (no meter documentos poco relacionados); hasta implementarlo, el comportamiento actual queda aceptado a sabiendas.

### P14 — Privacidad de logs (A-32) → Responsable de TI/compliance
**Pregunta**: ¿hay política aplicable a los logs con texto de usuarios?
**Respuesta simulada**: los logs son **internos y de uso operativo**; no hay política externa aplicable hoy; en modernización se pide reducir el registro del texto completo del usuario a nivel DEBUG.

### P15 — Dependencias y runtime (A-36) → Responsable técnico
**Pregunta**: ¿quién audita dependencias y cuándo? ¿Salir de Python 3.8?
**Respuesta simulada**: auditoría **trimestral por el equipo de desarrollo**; **sí se aprueba** migrar de Python 3.8 en modernización.

### P16 — Contrato de características (C-01) → Responsable técnico
**Pregunta**: ¿qué convención define las características del modelo?
**Respuesta simulada**: la convención oficial es la de **Open-Meteo** (la del endpoint `/predict`); el método del dominio (`to_features`) debe alinearse en modernización.

### P17 — Contrato de errores (C-03/C-04) → Responsable técnico
**Pregunta**: ¿un único código y formato de error?
**Respuesta simulada**: **sí**: un solo contrato (400 para entrada inválida, 404 no encontrado, 500 genérico sin detalle interno) idéntico en `/chat` y `/predict`; a definir en la spec formal.

### P18 — Configuración oficial (C-05/C-10) → Responsable técnico
**Pregunta**: ¿dónde viven las constantes de contrato (ruta del modelo, horizontes, embeddings)?
**Respuesta simulada**: **en settings**, único sitio; los defaults de clases y constantes de scripts pasan a leer de ahí en modernización. Ruta oficial del modelo: `models/model.pkl`.

---

## 2. Decisiones propuestas y su efecto sobre el registro de anomalías

| A-ID | Decisión propuesta (simulada) | Clasificación resultante* | Tratamiento acordado |
|---|---|---|---|
| A-01 | Reentrenar en modernización (P1) | BUG HISTÓRICO CON DEPENDIENTES (confirmada) | corregir con reentrenamiento; no retroactiva; prohibido citar 0,37 |
| A-02 | Ítem del reentrenamiento; no anunciar soporte (P1/P8) | BUG HISTÓRICO CON DEPENDIENTES | documentar ciudades no soportadas |
| A-03 | Corregir en modernización (P16) | BUG A SECAS | corregir tras caracterizar |
| A-04 | Aproximación provisional; alinear con reentrenamiento (P2) | BUG HISTÓRICO CON DEPENDIENTES | especificar tal cual ahora |
| A-05 | Interno aceptado; detalle de error no (P4) | INTENCIONAL (auth) + BUG A SECAS (detalle) | corregir detalle en modernización |
| A-06 | Ruta oficial `models/model.pkl` en settings (P18) | BUG A SECAS | unificar en modernización |
| A-07 | Horizontes oficiales 6/12/24 (P5) | BUG A SECAS (validación) | validar contrato en modernización |
| A-08 | 48/72/168 descartados del API (P5) | INTENCIONAL (política) | especificar tal cual |
| A-09 | Solo local; checklist de despliegue (P6) | INTENCIONAL (ámbito local) | documentar restricción |
| A-10 | Corregir en modernización (—) | BUG A SECAS | transacción única |
| A-11 | Declarar dependencias existentes (P15) | BUG A SECAS | corregir en modernización |
| A-12 | Caracterizar antes de tocar (—) | BUG A SECAS | tests de caracterización |
| A-13 | Settings único sitio (P18) | ACCIDENTAL | unificar en modernización |
| A-14 | Documentar sin especificar (—) | ACCIDENTAL | — |
| A-15 | Modelo oficial: transacción por operación (implícito P7/P16) | ACCIDENTAL | documentar |
| A-16 | Definición única de búsqueda en spec (P17) | ACCIDENTAL | documentar |
| A-17 | Alembic fuente de verdad; db-sync deprecado (P7) | INTENCIONAL (con decisión) | documentar decisión |
| A-18 | Descarte confirmado (—) | BUG A SECAS | especificar tal cual |
| A-19 | Sesión por proceso aceptada; contrato pendiente (P3) | **PENDIENTE (contrato del proveedor sin aportar)** | especificar tal cual |
| A-20 | Solo ciudades entrenadas soportadas (P8) | INTENCIONAL (política) | especificar tal cual |
| A-21 | Propietario: equipo de datos/ML (P9) | INTENCIONAL (regla protegida) | restricción dura en spec |
| A-22 | Provisional; versión real en modernización (P10) | INTENCIONAL (provisional) | especificar tal cual |
| A-23 | Documentar sin especificar (—) | ACCIDENTAL | — |
| A-24 | forecasts = pendiente; models = descartada (P11) | INTENCIONAL (decisión) | tabla forecasts a spec futura; models a retirar |
| A-25 | Limpieza en modernización (—) | ACCIDENTAL | — |
| A-26 | Documentar sin especificar (—) | ACCIDENTAL | — |
| A-27 | Contrato único de errores (P17) | ACCIDENTAL | definir en spec |
| A-28 | Contrato único de errores (P17) | ACCIDENTAL | definir en spec |
| A-29 | Especificar tal cual (—) | ACCIDENTAL | — |
| A-30 | Aceptado de momento; histórico en deseos (P12) | INTENCIONAL (provisional) | especificar tal cual |
| A-31 | Umbral deseado; actual aceptado a sabiendas (P13) | INTENCIONAL (transicional) | especificar tal cual + deseo |
| A-32 | Logs internos; reducir texto en modernización (P14) | INTENCIONAL (ámbito interno) | documentar + mejora |
| A-33 | Corregir en modernización (—) | BUG A SECAS | — |
| A-34 | Documentar sin especificar (—) | ACCIDENTAL | — |
| A-35 | Documentar sin especificar (—) | ACCIDENTAL | — |
| A-36 | Auditoría trimestral; salir de 3.8 aprobado (P15) | DECIDIDA (pendiente auditoría real) | plan de migración |
| A-37 | Resolver versiones al crear tests/ (—) | ACCIDENTAL | — |
| A-38 | Documentar sin especificar (—) | ACCIDENTAL | — |
| A-39 | Sin decisión explícita (—) | **PENDIENTE** | ¿redondeo en la UI? |
| A-40 | Documentar sin especificar (—) | ACCIDENTAL | — |

\* Clasificación sellada como INTENCIONAL **solo tras ratificación real** (aviso de simulación).

## 3. Condiciones, prohibiciones e información nueva capturada (no preguntadas)

1. **Prohibición**: citar el 0,37 como fiabilidad del producto (es métrica
   entre ciudades, A-01).
2. **Condición**: el coste mensual del LLM no puede crecer por encima del
   doble del gasto actual (P3).
3. **Condición**: toda llamada al LLM se anota en el presupuesto mensual de
   operación (P3).
4. **Información nueva**: mercado prioritario **España**; Madrid ciudad de
   referencia; consultas en inglés secundarias (P8).
5. **Condición**: la semántica de lags debe fijarse ANTES de reentrenar (P2).
6. **Condición**: prohibido desplegar en producción sin sobreescribir las
   credenciales por defecto (P6).
7. **Información nueva**: se desea un histórico consultable de predicciones
   (la tabla `forecasts` recupera estatus de requisito, P11).
8. **Condición**: la puntuación de similitud del RAG debe tener umbral
   mínimo en la modernización (P13).
9. **Condición**: los logs de texto completo del usuario pasan a DEBUG en la
   modernización (P14).

## 4. Preguntas sin respuesta concluyente

1. **A-19**: contrato y coste del endpoint OpenCode Go — pendiente de aportar
   copia del contrato (respondente: compras/proveedor).
2. **A-21**: nombre concreto del responsable del modelo (el rol está
   decidido, la persona no).
3. **A-39**: política de redondeo en la presentación — no se preguntó ni se
   decidió.

## 5. Estado resultante de la lista PENDIENTES

Con las respuestas simuladas, de las 13 PENDIENTES del registro quedan **3
sin respuesta concluyente** (A-19 contrato, A-21 responsable nominal, A-39
redondeo). **En una entrevista real**, el acta solo cerraría la lista con
respuestas de personas identificadas; este documento es un simulacro de
método, no una ratificación.

## 6. Próximos pasos propuestos

1. Realizar la entrevista real (guion: preguntas P1-P18 + A-39) con
   participantes con nombre y fecha → ratificar o corregir cada decisión.
2. Aportar la copia del contrato del LLM (resuelve A-19).
3. Actualizar `registro-de-anomalias.md` con las decisiones ratificadas y
   vaciar la lista PENDIENTES.
4. Solo entonces: `/speckit.specify` sobre la base documentada
   (especificación formal del comportamiento protegido).

## 7. Pendiente para próxima ronda

Preguntas sin respuesta concluyente y preguntas nuevas surgidas de las
respuestas del negocio (agenda de la siguiente conversación; todas exigen
respondente con nombre y fecha reales):

1. **A-19** — Copia del contrato y coste del endpoint OpenCode Go
   (respondente: compras/proveedor). La sesión por proceso quedó aceptada.
2. **A-21** — Nombre concreto del responsable de regenerar `model.pkl`
   (el rol quedó decidido: equipo de datos/ML).
3. **A-39** — Política de redondeo en la presentación de predicciones
   (no se preguntó; sin respuesta concluyente).
4. **A-41 (nueva)** — ¿Se alinea el dataset (ciudades españolas
   prioritarias) y el idioma de consulta con el mercado declarado, dentro
   del reentrenamiento de A-01?
5. **H13 (nueva)** — ¿La checklist de despliegue existe por escrito? ¿Quién
   la ejecuta y quién la audita?
6. **H14 (nueva)** — ¿Desde cuándo rige la prioridad de mercado
   (España/Madrid)? ¿Hay documento estratégico que la respalde?
7. **Ratificación real** — Todas las decisiones P1-P18 de esta acta simulada
   requieren confirmación por persona identificada antes de sellar
   clasificaciones INTENCIONAL.
