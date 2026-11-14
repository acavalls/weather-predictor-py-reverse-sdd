# AGENTS.md

Instrucciones para agentes de código que trabajen en este repositorio.

## Contexto del proyecto

Agente de predicción climática conversacional (`weather-agent`): API FastAPI
con capa de ML (scikit-learn) y agente RAG. Arquitectura hexagonal en `src/`
(`domain`, `application`, `infrastructure`). Infraestructura: PostgreSQL con
Alembic (`docker-compose.yml`, `init.sql`).

## Constitución (obligatoria)

Lee y cumple `.specify/memory/constitution.md` antes de cualquier cambio.
Estamos en fase de **documentación y protección**, no de mejora:

1. **El comportamiento actual es sagrado.** Ningún cambio de comportamiento
   observable, aunque parezca un error. No corregir bugs: registrarlos.
2. **Evidencia obligatoria.** Toda afirmación sobre el sistema debe ir
   acompañada de fichero y líneas de código, dato real de la base de datos, o
   testimonio del negocio (con nombre y fecha). Las suposiciones se marcan
   como SUPOSICIÓN y se convierten en preguntas.
3. **Los hallazgos no se corrigen, se registran.** Bugs, riesgos y rarezas van
   al registro de anomalías con su clasificación.
4. **Cero dependencias nuevas y cero refactors.** No añadir paquetes ni
   reorganizar código. Los tests de caracterización usan exclusivamente
   pytest (configurado en `pyproject.toml` y `Makefile`).
5. **Español de España.** Toda documentación, comentarios, registros y
   mensajes producidos van en español de España.

## Comandos

```bash
make install         # crear venv e instalar dependencias
make dev             # uvicorn con recarga en :8000
make test            # pytest (PYTHONPATH=.)
make test-coverage   # pytest con cobertura (mínimo 80%)
make lint            # ruff check
make format          # ruff format
make type            # mypy sobre src/
make check           # lint + format --check + mypy
make db-migrate MSG="..."  # generar migración Alembic
make db-upgrade      # aplicar migraciones
docker compose up -d # levantar PostgreSQL
```

## Convenciones

- Linter y formateador: ruff (línea 120, comillas dobles). Tipado: mypy.
- Configuración de pytest en `pyproject.toml` (`tests/` es el directorio de
  tests; aún no existe, créalo solo para tests de caracterización).
- Al terminar cambios, ejecuta `make check` y `make test`.
- No modificar `requirements.txt` ni `pyproject.toml` en cuanto a
  dependencias (Principio 4 de la constitución).
- No hacer commit sin que el usuario lo pida explícitamente.
