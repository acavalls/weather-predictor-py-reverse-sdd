<!--
  SYNC IMPACT REPORT
  ==================
  Versión: (sin ratificar, plantilla vacía) → 1.0.0
  Principios modificados: ninguno (adopción inicial; los 5 principios se
  redactan por primera vez a partir del input del negocio)
  Secciones añadidas:
    - Principios Fundamentales (5 principios)
    - Restricciones Adicionales
    - Flujo de Trabajo de Documentación y Protección
    - Gobernanza
  Secciones eliminadas: ninguna
  TODOs/elementos diferidos:
    - PRINCIPIO 4: el input original indicaba `node:test` (runner nativo de
      Node), pero el proyecto es Python (pyproject.toml:
      `name = "weather-agent"`). Resuelto en revisión: el runner oficial para
      los tests de caracterización es pytest, ya configurado en
      `pyproject.toml` y `Makefile` (sin dependencias nuevas, conforme al
      Principio 4).
  Próxima revisión de cumplimiento: al inicio del módulo siguiente.
-->

# Constitución del Agente de Predicción Climática

## Principios Fundamentales

### I. El comportamiento actual es sagrado

Ningún cambio de comportamiento observable está permitido en esta fase, ni
siquiera cuando el comportamiento parezca un error. El sistema se documenta y
protege tal como es; corregirlo pertenece a un módulo posterior.

### II. Evidencia obligatoria

Toda afirmación sobre lo que el sistema hace DEBE ir acompañada de su
evidencia, que puede ser: fichero y líneas de código, dato real de la base de
datos, o testimonio del negocio (con nombre y fecha). Las suposiciones se
marcan explícitamente como SUPOSICIÓN y se convierten en preguntas.

### III. Los hallazgos no se corrigen, se registran

Los bugs, riesgos y rarezas detectados DEBEN registrarse en el registro de
anomalías con su clasificación correspondiente. Corregirlos es una decisión
del módulo siguiente, no de esta fase.

### IV. Cero dependencias nuevas y cero refactors

No se añade ningún paquete nuevo ni se reorganiza código en esta fase.

### V. Español de España

Todo el contenido producido en esta fase (documentación, constitución,
registros, tests y comentarios) DEBE estar en español de España, como el
resto del proyecto y de sus usuarios.

## Restricciones Adicionales

- Está prohibido añadir dependencias (paquetes, librerías, imágenes) durante
  esta fase. `requirements.txt` y `pyproject.toml` DEBEN permanecer intactos
  en cuanto a dependencias.
- Está prohibido refactorizar: no se renombra, mueve ni reorganiza código
  fuente. Solo se permite añadir artefactos de documentación y tests de
  caracterización.
- Los tests de caracterización se ejecutarán únicamente con pytest (runner ya
  configurado en `pyproject.toml` y `Makefile`), sin frameworks de testing
  adicionales.

## Flujo de Trabajo de Documentación y Protección

1. Toda exploración del código DEBE documentar el comportamiento observado
   con su evidencia (Principio II).
2. Cada hallazgo (bug, riesgo, rareza) DEBE registrarse en el registro de
   anomalías con clasificación, sin intentar corregirlo (Principio III).
3. Las SUPOSICIONES se marcan como tales y se listan como preguntas abiertas
   hasta disponer de evidencia o testimonio del negocio.
4. La revisión de cumplimiento constitucional es obligatoria antes de dar por
   cerrada cualquier entrega de esta fase.

## Gobernanza

- Esta constitución prevalece sobre cualquier otra práctica, convención o
  instrucción del proyecto durante la fase de documentación y protección.
- Las enmiendas requieren: documentación del cambio, versión actualizada
  según versionado semántico y registro en la sección de historial.
- Versionado semántico: MAJOR para cambios incompatibles de gobernanza o
  redefinición/eliminación de principios; MINOR para nuevos principios o
  secciones o ampliación sustancial de la guía; PATCH para aclaraciones y
  correcciones de redacción sin impacto semántico.
- Toda revisión o PR DEBE verificar el cumplimiento de estos principios; la
  complejidad añadida debe justificarse frente a ellos.

**Versión**: 1.0.0 | **Ratificado**: 2026-11-14 | **Última modificación**: 2026-11-14
