# LEEME — Golden master del flujo central (/predict)

## Qué es

`master.json` es la fotografía de la SALIDA COMPLETA del caso de uso de
predicción (`PredictHandler.execute`) para un juego fijo de 12 casos de
entrada, generada con `scripts/generate_golden_master.py` contra el modelo
real `models/model.pkl` el 2026-11-14 (md5 truncado del artefacto:
`b59e0918`). Incluye todos los decimales que produce el sistema (RN-13: el
sistema no redondea) y claves ordenadas para que el diff sea estable.

Los 12 casos cubren: ciudades dentro y fuera del OneHot del modelo (A-02:
Tokyo/São Paulo/Atlantis se codifican a ceros), las dos rutas de conversión
de condiciones (chat a ceros, A-03/C-01), fronteras de horizontes (solo 6;
[6,999] con descarte silencioso, RN-05; dependencia de la predicción de los
horizontes pedidos, A-43), extremos físicos aceptados (RN-04), fin de
semana (frontera day_of_week>=5), 29 de febrero (bisiesto) y fin de año.

## Cuándo DEBE regenerarse (y cuándo NO)

- **NO se regenera** para "hacer que pase" un test. Si el test del master
  falla, el primer paso es investigar QUÉ cambió: ¿el código? ¿el modelo?
  ¿el entorno?
- **SÍ se regenera** únicamente cuando existe una decisión de negocio
  DOCUMENTADA (constitución, Principio II) que cambie el comportamiento
  protegido: reentrenamiento del modelo, cambio de contrato de la API,
  corrección aprobada en modernización, etc. La decisión se anota en el
  registro de anomalías con su testigo, y el master nuevo se genera y
  versiona en el mismo commit.

## Cómo regenerarlo

```bash
PYTHONPATH=. venv/bin/python scripts/generate_golden_master.py
```

El script ejecuta los 12 casos con reloj congelado y proveedor
meteorológico fijo (sin red) y reescribe este fichero. El `model_version`
(md5 del binario) viaja dentro del master: si cambia el artefacto, el
master debe regenerarse como parte de la misma decisión.
