**Idioma:** [English](analytical_decisions.md) | Español

# Decisiones analíticas

> Un resumen breve para quien lee el repositorio. Las definiciones de referencia están en [`kpi_definitions.es.md`](kpi_definitions.es.md), [`assumptions.es.md`](assumptions.es.md), [`canonical_schema.es.md`](canonical_schema.es.md) y [`kpi_spec.es.md`](kpi_spec.es.md); si esta página y esos documentos no coinciden, prevalecen esos documentos. Todos los valores de este repositorio son sintéticos.

## 1. A quién se cuenta (poblaciones y denominadores)

| Decisión | Regla | Por qué |
|---|---|---|
| Lead elegible | `is_duplicate = false` e `is_reactivation = false`; las reactivaciones se informan aparte | los duplicados y los leads que vuelven inflarían la base |
| Denominador del KPI principal | **todos** los leads elegibles maduros, de las dos rutas | la etapa Opportunity del CRM dejaría fuera la ruta bot, que agenda entrevistas directamente |
| Numerador del KPI principal | leads elegibles maduros con al menos una cita **realizada** | una cita agendada o un no-show no es una entrevista |
| Una unidad por métrica | las métricas por lead y por cita nunca se mezclan: el show rate se informa **por cita** y **por lead** | responden a preguntas distintas |
| Cita elegible | de un lead elegible, no sustituida por una reprogramación y agendada como muy tarde en la fecha de corte | una cita reprogramada se contaría dos veces |
| Denominador del SLA | leads manuales elegibles creados al menos 24 h antes de la fecha de corte; los leads sin intento **siguen en el denominador** | quitarlos ocultaría los peores casos |
| Percentiles de primera respuesta | solo leads con intento (las duraciones observadas) | sin final no se puede calcular una duración |

## 2. Cuándo (cohorte, periodo y fecha de corte)

- **Fecha de corte.** Un único corte fijo: 2025-12-31 23:59. Todo estado ("abierto", "vencido") se mide en ese momento.
- **Cohorte.** El mes de `created_at`. Las conversiones se miden solo con leads **maduros**: `corte − created_at ≥ 60 × 24 h`, por lead y con marcas de tiempo completas. Las cohortes parciales e inmaduras se etiquetan y nunca se comparan con las maduras.
- **Periodo.** El mes del evento (hora de la cita, actividad, matrícula); se usa para el show rate, la carga de trabajo y la gobernanza.
- **Horas.** El SLA y el seguimiento usan **horas naturales** (decisión documentada de v1); la cadencia de recuperación de entrevistas usa días laborables. Las horas naturales incluyen noches y fines de semana, y por eso las entradas en fin de semana puntúan peor en este escenario.
- **Zona horaria.** Los datos sintéticos usan marcas de tiempo locales. Los instantes UTC y las reglas de calendario local son una fase futura (F3.5), no implementada.

## 3. Datos ausentes y anomalías

- **Ausente no es cero.** Cuando a un dataset le falta lo que un KPI necesita, el KPI es `not_available` con un motivo y la lista exacta de campos que faltan, y no lleva valor, numerador ni denominador. Motivos: `HM` (sin hitos de etapa), `HF` (sin historial completo), `AUT` (sin indicador de automatización), `APT` (sin citas), `FLD` (campo no proporcionado), `DEN0` (denominador cero), `INSUF` (sin observaciones), `ORD` (orden de eventos indeterminado). Un cero real sigue siendo un 0 disponible.
- **Un nulo en una fila no es un campo ausente.** Lo resuelve la regla del KPI (por ejemplo, un lead sin intento no cumple el filtro del SLA y sigue en su denominador).
- **No se inventa historial.** El historial de etapas nunca se deduce de la etapa actual, las citas ni las actividades.
- **Un valor desconocido detiene el cálculo.** Un valor fuera del dominio declarado de un campo (por ejemplo, un origen de registro desconocido) es un error de datos, no una exclusión silenciosa.
- **Las anomalías se conocen por diseño.** El generador introduce anomalías de calidad y las lista en `data/dq_ground_truth.csv`; cada regla de detección se compara con esa verdad de referencia en la misma unidad, y las pruebas de mutación demuestran que las comprobaciones pueden fallar.

## 4. Lo que las cifras no muestran

Los resultados sintéticos reflejan los parámetros del escenario, no un equipo ni un mercado reales. No se afirma ningún efecto causal: intervenciones como el WhatsApp personal tienen efecto programado cero, y cualquier diferencia aparente es una asociación. La comparación entre asesores es exploratoria. Lista completa de límites: [`assumptions.es.md` §4](assumptions.es.md).
