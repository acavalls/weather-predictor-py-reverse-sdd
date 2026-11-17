# weather-agent — caso práctico de SDD sobre un proyecto desconocido

Este repositorio es un caso práctico de un enfoque de trabajo: cómo
enfrentarse a un proyecto **legacy o desconocido a priori** para poder
aplicar **Spec-Driven Development (SDD) con un agente de IA**.

La idea central: no se puede especificar (ni desarrollar) sobre un sistema
que nadie sabe cómo funciona. Primero se hace **ingeniería reversa** para
obtener la documentación funcional (mapa del sistema, flujos, riesgos,
memoria histórica), y solo entonces se aplican los comandos SDD
(`/speckit.specify`, `/speckit.plan`, `/speckit.tasks`, …) sobre una base
conocida y protegida.

El sistema de este repo —un agente de predicción climática conversacional.

Las reglas del juego están en la constitución:
`.specify/memory/constitution.md`.

## Cómo se ha generado la documentación

Los artefactos de este repositorio (constitución, instrucciones para agentes,
documentos de reconocimiento y la red de tests de caracterización) se han
generado conversando con un agente de código, a partir de los siguientes
prompts literales del usuario.
Se transcriben como parte del método: así queda constancia de qué pregunta
produce qué artefacto, replicable en otros proyectos legacy.

### 1. Constitución (`.specify/memory/constitution.md`)

Generada mediante el comando `/speckit.constitution` con el siguiente input:

```text
Redacta la constitución de este proyecto, que es un
agente de predicción climática.

El objetivo de esta fase es documentarlo y protegerlo, no
mejorarlo. Principios innegociables:

1. El comportamiento actual es sagrado. Ningún cambio de comportamiento
   observable, aunque el comportamiento parezca un error.
2. Evidencia obligatoria. Toda afirmación sobre lo que el sistema hace debe
   ir acompañada de su evidencia: fichero y líneas de código, dato real de
   la base de datos, o testimonio del negocio (con nombre y fecha). Las
   suposiciones se marcan como SUPOSICIÓN y se convierten en preguntas.
3. Los hallazgos no se corrigen, se registran. Bugs, riesgos y rarezas van
   al registro de anomalías con su clasificación; corregirlos es una
   decisión del módulo siguiente, no de este.
4. Cero dependencias nuevas y cero refactors. No se añade ningún paquete ni
   se reorganiza código en esta fase; los tests de caracterización usarán
   exclusivamente el runner nativo.
```

### 2. Instrucciones para agentes (`AGENTS.md`)

Prompt:

```text
crea un AGENTS.md apropiado, que tenga en cuenta el fichero de
constitución recién creado
```

### 3. Reconocimiento (`specs/000-reconocimiento/`)

#### 3.1 Mapa del sistema (`mapa-sistema.md`)

Prompt:

```text
Explora todo el proyecto y genera specs/000-reconocimiento/mapa-sistema.md
con el mapa del sistema. Para cada módulo o fichero relevante: (1) su
responsabilidad en una frase de negocio, no técnica; (2) de qué otros
módulos depende y quién depende de él; (3) una estimación de su criticidad
para el negocio (alta/media/baja) con justificación. Añade al final:
(a) un diagrama en texto de las dependencias; (b) la lista de tecnologías
y versiones reales que usa el proyecto; (c) un apartado
"Zonas oscuras" con todo lo que exista en el proyecto y no encaje en el
mapa: código muerto, ficheros huérfanos, funcionalidades a medias.
Constitución aplicable: toda afirmación con su evidencia (fichero y líneas).
```

#### 3.2 Flujo de aplicación (`flujo-aplicacion.md`)

Prompt:

```text
Documenta en specs/000-reconocimiento/flujo-aplicacion.md el ciclo de vida
completo de una pregunta lanzada por el usuario sobre el clima, siguiendo el código paso a paso.
Cubre todos los casos diferentes que puedan darse (compruébalo, no lo
supongas). Para cada caso: qué entradas recibe, qué módulos atraviesa y en qué orden, etc.
Señala explícitamente cualquier punto del flujo donde dos caminos hagan "lo mismo" con código distinto.
Evidencia obligatoria en cada paso.
```

#### 3.3 Registro de riesgos (`registro-riesgos.md`)

Prompt:

```text
Genera specs/000-reconocimiento/registro-riesgos.md con la deuda técnica y
los riesgos VISIBLES del proyecto, sin corregir nada. Busca específicamente:
secretos o credenciales en el código; operaciones de base de datos de varios
pasos sin transacción (y qué pasaría si fallan a medias); condiciones de
carrera (lecturas-modificaciones-escrituras concurrentes, contadores);
validaciones incompletas o desactivadas; manejo de fechas casero y sus casos
límite; dependencias muertas, obsoletas o con avisos de seguridad; y
cualquier discrepancia entre lo que los comentarios prometen y lo que el
código hace. Formato: tabla con ID (R1, R2...), descripción, evidencia,
impacto de negocio en una frase, y probabilidad estimada de que muerda
(alta/media/baja). Ordena por impacto × probabilidad. No propongas
soluciones todavía: solo el registro.
```

#### 3.4 Memoria histórica (`memoria-historica.md`)

Prompt:

```text
Recorre todos los comentarios del proyecto y extrae en
specs/000-reconocimiento/memoria-historica.md una cronología de eventos y
decisiones del sistema: incidentes mencionados (con fecha si consta),
decisiones de negocio atribuidas a personas, advertencias del tipo "no
tocar" con su motivo, y trabajos abandonados. Presenta cada entrada como:
fecha aproximada, qué pasó o qué se decidió, quién aparece implicado,
dónde está el comentario (fichero y línea), y qué pregunta deberíamos
hacerle al negocio al respecto.
```

#### 3.5 Reglas de negocio (`reglas-de-negocio.md`)

Prompt:

```text
Toma specs/000-reconocimiento/mapa-sistema.md y selecciona los módulos de lógica de negocio central (obligatorios criticidad ALTA) junto con las utilidades de las que dependan.
Extrae en specs/000-reconocimiento/reglas-de-negocio.md
TODAS las reglas de negocio que implementan, escritas como reglas de
negocio, no como descripción del código. Para cada regla:
- identificador (RN-01, RN-02...);
- enunciado en lenguaje de negocio;
- un ejemplo concreto, calculado ejecutando mentalmente el
  código;
- evidencia: función, fichero y líneas;
- clasificación provisional: INTENCIONAL (señales de decisión deliberada:
  comentarios, coherencia interna, testimonio), ACCIDENTAL (efecto
  colateral de la implementación) o DUDOSA (indecidible desde el código).

Presta atención especial a los sospechosos habituales:
- redondeos y truncamientos, y el ORDEN en que se aplican;
- fronteras exactas de todo umbral, tramo o límite (¿> o >=? ¿el valor
  justo entra o no entra?);
- manejo de fechas;
- valores especiales: cero, negativos, vacíos y duplicados;
- constantes mágicas y tablas hardcodeadas;
- toda discrepancia entre lo que dicen los comentarios y lo que hace el
  código: cada discrepancia es un hallazgo, nunca un descuido a ignorar.

No corrijas nada. Constitución aplicable: toda afirmación con su
evidencia; las suposiciones se marcan como SUPOSICIÓN y se convierten
en preguntas.
```

#### 3.6 Contradicciones (`contradiccion-01` a `contradiccion-10`)

Prompt:

```text
Busca en todo el proyecto conceptos de negocio implementados MÁS DE UNA
VEZ: el mismo cálculo, validación, formato o transformación escrito en dos
o más sitios. Pistas para encontrarlos: los puntos que flujo-*.md señala
como "dos caminos hacen lo mismo con código distinto"; funciones de nombre
parecido en módulos distintos; lógica inline en scripts o jobs que
reimplementa funciones que ya existen en la aplicación; y validaciones que
se repiten con criterios diferentes.

Para cada duplicidad, documenta en
specs/000-reconocimiento/contradiccion-NN-<nombre>.md:
(1) las implementaciones implicadas, con evidencia (fichero, función,
    líneas) y qué camino del sistema usa cada una;
(2) ¿usan la misma convención o algoritmo? Compáralas paso a paso;
(3) si difieren, construye ejemplos concretos donde produzcan resultados
    DISTINTOS para la misma entrada —con datos reales de producción si es
    posible— y cuantifica la divergencia;
(4) en qué circunstancias se manifiesta la divergencia y en cuáles ambas
    coinciden (esto suele explicar por qué nadie la ha detectado);
(5) la historia probable de cómo se llegó aquí, reconstruida desde los
    comentarios, el estilo del código y la cronología del proyecto.

NO decidas cuál de las implementaciones es "la correcta": esa es una
pregunta de negocio, no técnica. No corrijas nada. Cada contradicción
encontrada terminará como entrada del registro de anomalías y como
pregunta del guion de entrevista al negocio.
```

#### 3.7 Registro de anomalías (`registro-de-anomalias.md`)

Prompt:

```text
Consolida todos los hallazgos del reconocimiento y la ingeniería inversa
en specs/000-reconocimiento/registro-de-anomalias.md. Fuentes de entrada,
recórrelas TODAS y no dejes ninguna huérfana:
- las reglas clasificadas como DUDOSAS o ACCIDENTALES en
  reglas-de-negocio.md (las INTENCIONALES con historia de incidente
  también entran: son anomalías positivas, reglas protegidas);
- todas las contradicciones documentadas en contradiccion-*.md;
- las entradas del registro-riesgos.md;
- las discrepancias comentario-vs-código y los "no tocar" de
  memoria-historica.md;
- las respuestas de entrevista-negocio.md y los resultados de la
  arqueología de datos, que son las que permiten cerrar clasificaciones.

Una entrada por anomalía (A-01, A-02...), cada una con:
- descripción en una frase;
- evidencia, citando qué testigos la respaldan: CÓDIGO (fichero y
  líneas), DATOS (consulta y resultado) y/o NEGOCIO (quién lo dijo y
  cuándo);
- clasificación final: INTENCIONAL / ACCIDENTAL / BUG HISTÓRICO CON
  DEPENDIENTES / BUG A SECAS. Regla innegociable: nada se clasifica
  como INTENCIONAL sin al menos dos de los tres testigos a favor. Si
  falta el testimonio del negocio o el veredicto de los datos, la
  clasificación queda como PENDIENTE con la pregunta exacta que la
  desbloquearía;
- quién o qué depende del comportamiento actual (personas, procesos
  externos, documentos ya emitidos), o "nadie identificado";
- tratamiento acordado: especificar tal cual / documentar sin
  especificar / corregir en fase de modernización, con qué precauciones
  y si la corrección puede o no ser retroactiva;
- decisión de negocio pendiente, si la hay, con su responsable.

Ordena por impacto. Cierra con una tabla resumen
(ID / clasificación / tratamiento / decisión pendiente) y con la lista
de clasificaciones PENDIENTES: esa lista debe quedar VACÍA antes de
escribir las specs formales; si no lo está, es la agenda de la próxima
conversación con el negocio.
```

#### 3.8 Acta de entrevista de negocio simulada (`acta-entrevista-negocio.md`)

Prompt (el consultor responde también como cliente, con la respuesta de
mayor lógica; el resultado queda marcado como simulado y pendiente de
ratificación real):

```text
Simulemos la entrevista de negocio. Prepara tú las preguntas a partir de
specs/000-reconocimiento/: las clasificaciones PENDIENTES y DUDOSAS del
registro de anomalías, las contradicciones documentadas y las preguntas
abiertas de la memoria histórica. Formúlalas como preguntas decidibles:
contexto mínimo en lenguaje no técnico, ejemplo con números reales,
respuesta por sí/no o elección entre opciones, sin sugerir la respuesta;
ordénalas de más a menos impacto económico. Tú eres el consultor; yo haré
de cliente y responderé en el papel de la persona del negocio que
corresponda (dime a quién va dirigida cada una). Una pregunta por turno;
si mi respuesta no decide la cuestión, repregunta o anótala como "sin
respuesta concluyente"; apunta toda condición, prohibición o información
nueva que suelte aunque no la hayas preguntado. Al terminar, vuelca tus
notas, genera el acta.
```

Opcional:

```text
Responde tu todas las preguntas como si fueras el cliente con la
respuesta que tenga más lógica y finaliza el acta de la reunión.
```

#### 3.9 Propagación del acta al registro (`registro-de-anomalias.md`, `registro-riesgos.md`, `memoria-historica.md`)

Prompt:

```text
A partir del acta:

1. Propaga el acta al registro de anomalías: cierra las PENDIENTES
   que el acta resuelva, añadiendo a su evidencia el testigo NEGOCIO
   como referencia (acta, pregunta, persona, fecha). Registra el
   cambio de clasificación, no lo sobrescribas en silencio.
2. Lo que el negocio revele y no estuviera documentado (procesos
   manuales, dependencias externas, incidentes no registrados) genera
   entradas NUEVAS en el registro de anomalías, el registro de
   riesgos o la memoria histórica, según corresponda, citando el acta.
3. Las preguntas sin respuesta concluyente, y las preguntas nuevas
   que hayan surgido, van a la sección "Pendiente para próxima ronda"
   del acta.
4. Termina con el estado de la lista PENDIENTE del registro: si no
   queda vacía, esa lista es la agenda de la siguiente conversación
   con el negocio; si queda vacía, el reconocimiento está listo para
   pasar a specs formales.
```

Los commits intermedios se pidieron con prompts mínimos («commit», «si,
haz un commit de la propagación»), siempre a petición explícita del
usuario.

#### 3.10 Red de tests de caracterización (`tests/`, `scripts/generate_golden_master.py`)

Prompt:

```text
Crea la red de characterization tests del proyecto: tests que congelan
el comportamiento ACTUAL del sistema, tal cual es, para detectar
cualquier cambio futuro. Restricciones de la constitución: cero
dependencias nuevas y cero cambios en el código de producción; usa el
runner de tests nativo del stack (o el que ya exista en el proyecto).

REGLAS DE ORO, innegociables:
- El valor esperado de cada test es EL QUE EL CÓDIGO ACTUAL PRODUCE.
  Ejecuta cada caso y transcribe el resultado real, aunque contradiga
  la norma, la lógica o la documentación.
- Si un test falla, corrige el TEST (transcribiste mal la realidad),
  jamás el código.
- Si al ejecutar descubres un comportamiento no documentado en el
  reconocimiento, no lo "arregles": añádelo como entrada nueva al
  registro de anomalías y congélalo.

QUÉ CUBRIR (derívalo de los artefactos, no lo inventes):
1. Alcance: los módulos de criticidad ALTA de mapa-sistema.md,
   empezando por las funciones puras (cálculo y validación sin IO),
   que son las congelables sin infraestructura.
2. Una batería por cada regla de reglas-de-negocio.md, usando su
   ejemplo numérico como caso de contraste: si tu transcripción no
   coincide con el ejemplo del documento, PARA e investiga cuál de
   los dos está mal antes de continuar.
3. Un test por cada anomalía ejecutable del registro, con nombre
   prefijado "CONGELA comportamiento actual:" y comentario que remite
   a su ID. Para las contradicciones (conceptos implementados más de
   una vez), congela CADA implementación por separado, cada una con
   su resultado divergente.
4. Para todo umbral, tramo o frontera: los tres puntos por los dos
   lados (justo debajo / el valor exacto / justo encima).
5. Los sospechosos habituales: redondeos con casos de coma flotante,
   fechas en fin de mes, fin de año y febrero bisiesto, cero,
   negativos, vacíos y valores inexistentes.

GOLDEN MASTER del flujo central de negocio (identifícalo en los
flujo-*.md): diseña un juego FIJO de 8-12 casos de entrada que entre
todos ejerciten las reglas y anomalías principales; genera la salida
completa, con todos los decimales, a un fichero master de formato
estable y claves ordenadas; y crea el test que regenera y compara en
profundidad, con mensajes de fallo que señalen el caso y el campo
exactos. Añade junto al master un LEEME: qué es, cuándo DEBE
regenerarse (solo con decisión de negocio documentada) y cómo.

Al terminar: ejecuta la suite completa, itera hasta el verde total y
añade el script de test al manifiesto del proyecto. Entrega un resumen
final: tests creados, anomalías congeladas, y qué partes del sistema
quedan FUERA de la red y por qué (rutas, jobs, IO), como registro de
cobertura pendiente para la siguiente fase.
```

Resultado: 190 tests en verde (pytest, ya configurado en el proyecto),
golden master de 12 casos del flujo `/predict` con su LEEME y target
`make golden-master`, y dos anomalías nuevas registradas por hallazgos de
la caracterización (A-42: extracción de ciudad sin ñ/ã; A-43: la
predicción de un horizonte depende de los horizontes pedidos).

#### 3.11 Propuesta de partición en specs formales (`propuesta-particion-specs.md`)

Prompt:

```text
Vamos a decidir la partición del sistema en specs formales. Precondición:
la lista PENDIENTE del registro de anomalías debe estar vacía; si no lo
está, para y dime qué falta por cerrar. Lee todos los artefactos de
specs/000-reconocimiento/ y genera specs/000-reconocimiento/propuesta-particion-specs.md.

PARTE 1 — La partición. Reglas:
- Las specs se dividen por DOMINIO DE NEGOCIO, nunca por fichero ni por
  capa técnica. Un dominio = un conjunto de reglas que el negocio decide
  junto y que puede evolucionar sin arrastrar a los demás.
- Para cada spec propuesta: nombre y número; alcance en 2-3 frases;
  módulos de código que la evidencian; reglas RN-* que le pertenecen;
  anomalías A-* que le pertenecen, con su clasificación y tratamiento;
  characterization tests que la respaldan (y si el golden master la
  cubre); y su dueño natural del negocio: quién respondió sobre estas
  cuestiones en las actas.
- Reparto de contradicciones: la convención declarada vigente va a la
  spec del dominio que posee la regla; la implementación divergente se
  referencia como anomalía en la spec del camino que la usa.
- Criterio de tamaño: cada spec debe poder revisarla el negocio en una
  sentada (~30 min). Si excede, divídela; si dos specs se citarían
  mutuamente en más de la mitad de sus requisitos, fusiónalas.
- Completitud: ninguna regla RN-* ni anomalía A-* puede quedar sin spec
  asignada; lo que excluyas (p. ej. riesgos puramente técnicos sin
  comportamiento de negocio), justifícalo.
- Señala los casos frontera —conceptos que podrían caer en dos specs—
  con tu recomendación y el criterio aplicado.

PARTE 2 — Para cada spec propuesta, su descripción LISTA para lanzar
con /speckit-specify, siguiendo la plantilla de spec inversa:
- Encuadre: "Spec de ingeniería inversa: documenta el comportamiento
  EXISTENTE de [dominio]. No es una feature nueva: es la especificación
  formal de lo que el sistema YA hace, para que sirva de contrato en la
  modernización."
- Reglas de la spec: cada requisito y criterio describe el
  comportamiento ACTUAL con su evidencia (fichero y función, o dato
  real); las anomalías NO se corrigen ni se omiten: se especifican tal
  cual funcionan hoy, referenciadas por su ID del registro; los
  criterios de aceptación deben ser verificables contra la suite de
  tests/, citando el test cuando exista; toda decisión de negocio se
  cita por su acta (documento, pregunta, persona, fecha).
- Alcance: enumera las reglas del dominio CON SUS VALORES CONCRETOS
  (umbrales exactos, convenciones, el ejemplo numérico canónico de cada
  regla tomado de reglas-de-negocio.md) y sus anomalías con el
  tratamiento acordado.
- Fuera de alcance: qué queda deliberadamente para otras specs,
  nombrándolas por número.

Cierra con la tabla resumen (spec → reglas → anomalías → dueño → tests)
y NO ejecutes ningún /speckit-specify: la propuesta se revisa y se
aprueba antes de invertir.
```

Resultado: 5 specs por dominio de negocio (datos meteorológicos,
predicción numérica, agente conversacional, entrenamiento/artefacto ML,
plataforma), 27/28 reglas y 43/43 anomalías asignadas, 7 casos frontera
documentados, y ninguna spec ejecutada (pendiente de aprobación).

Resultado: flujo `/speckit.specify` ejecutado sobre las 5 specs de la
partición, con plantilla de spec-kit adaptada a spec inversa (constitución
> plantilla genérica: la evidencia de fichero/línea es obligatoria), 5
checklists de calidad, 0 marcadores [NEEDS CLARIFICATION].

#### 3.12 Paquete de especificación (`specs/SPEC-PACK.md`)

Prompt:

```text
Ensambla el spec pack en specs/SPEC-PACK.md como documento de
entrada única al paquete. Estructura:
(1) Resumen ejecutivo PARA EL GERENTE, una página, sin tecnicismos: qué
    se ha hecho, qué se ha descubierto (las 3-4 anomalías con impacto, en lenguaje de negocio y con ejemplos), qué
    protección se ha instalado (los tests, explicados con una frase) y qué decisiones tiene
    pendientes el negocio, con recomendación.
(2) Inventario de riesgos priorizado (desde registro-riesgos.md y el
    registro de anomalías), cada uno con impacto en una frase y
    recomendación para continuar con la implementación.
(3) Índice comentado del paquete: mapa del sistema, glosario, las
    specs con su trazabilidad, el registro de anomalías, la memoria
    histórica, la entrevista de negocio y la suite de tests con
    instrucciones de ejecución.
(4) Estado de la red de seguridad: qué está congelado y qué no (rutas
    HTTP y remesa end-to-end quedan explícitamente señaladas como
    primera tarea de la siguiente fase).
Tono: profesional.
```

## Comandos

```bash
make install         # crear venv e instalar dependencias
make dev             # uvicorn con recarga en :8000
make test            # pytest (PYTHONPATH=.) — 190 tests de caracterización
make golden-master   # regenerar el golden master (solo con decisión de negocio documentada)
make lint / format / type / check   # ruff + mypy
docker compose up -d # levantar PostgreSQL
```

Detalles en `AGENTS.md`.
