**Idioma:** [English](kpi_spec.md) | Español

# Especificación declarativa de KPIs `kpi-spec/0.1` (F3.0, `v1.3.1-f3`)

> Todos los datos son **sintéticos**. F3.0 empieza a separar las definiciones de KPI del código específico de admisiones. Se declaran ocho KPIs en una configuración pequeña y un motor los evalúa sobre datasets canónicos **en paralelo** con `src/metrics.py`. `src/metrics.py` sigue siendo la referencia oficial y no se modifica. No es un framework universal: solo el perfil de admisiones, sin afirmaciones de portabilidad, sin CRM y sin datos reales.

## 1. Piezas

| Archivo | Función |
|---|---|
| [`schema/kpi_spec_v0.1.yaml`](../schema/kpi_spec_v0.1.yaml) | el lenguaje cerrado: claves, operaciones, filtros, relaciones de ratio, códigos de error y motivos de no disponibilidad |
| [`profiles/admissions/kpis.yaml`](../profiles/admissions/kpis.yaml) | los ocho KPIs de admisiones: campos, poblaciones y KPIs |
| `src/kpispec/spec.py` | carga y validación (la primera infracción → `KpiSpecError` con un código `K_*`; nada inválido se evalúa) |
| `src/kpispec/fields.py` | resolución de campos: valores, o el motivo por el que un campo no está disponible; se exigen los dominios declarados |
| `src/kpispec/engine.py` | poblaciones, filtros y operaciones; no importa `src/metrics.py` ni directa ni indirectamente (el adaptador solo lo carga en la ruta de metrics.py) |

## 2. El lenguaje (cerrado)

**Operaciones (5):** `count`, `share`, `ratio`, `duration_stat` (mediana, media o p90 con interpolación lineal, en horas o días) y `field_stat` (media; está en el catálogo, no se usa en F3.0). Numerador y denominador siguen la convención de F0:

| Operación | valor | numerador | denominador |
|---|---|---|---|
| `count` | n | n | null |
| `share` | subconjunto / población | n del subconjunto | n de la población |
| `ratio` | población A / población B | n de A | n de B |
| `duration_stat`, `field_stat` | estadístico | null | n de observaciones |

**Filtros (solo Y lógica):** `equals`, `in`, `not_null`, `is_null`, `age_at_least_days`, `created_before_snapshot_minus_hours`, `at_or_before_snapshot`, `weekday_in` (lunes = 0) y `duration_le_hours` (un fin vacío nunca cumple). No hay expresiones, OR ni código embebido: claves como `or`, `expr`, `formula`, `code`, `lambda`, `eval` o `sql` se rechazan (`K_FORBIDDEN_KEY`).

**Poblaciones:** tienen una `unit` (`lead` o `appointment`) o se definen `from` otra población más filtros adicionales. Un filtro solo puede leer campos de la unidad de la población (o del dataset).

## 3. Campos: nada se da por disponible

Cada campo declara su origen y cómo puede faltar:

| Forma del origen | Si falta la tabla o columna |
|---|---|
| `records.<col>`, `dataset.<col>` | el `if_missing` del campo (FLD en los campos de admisiones) |
| `records.<col>` con `via: appointments.record_id` | `if_missing` (APT) si no hay citas; FLD si falta la columna de records |
| `appointments.<col>` | `if_missing` (APT) si falta la tabla; FLD si solo falta la columna |
| `stage_first_entry.<etapa>` | `if_missing: HM` cuando el dataset no tiene hitos de etapa; `if_missing: HF` cuando no tiene historial completo de eventos (los hitos no bastan). Los ocho KPIs de F3.0 solo usan HM. |
| `profile.<función>` | se comprueba cada entrada de `needs`; por ejemplo, `first_human_attempt` necesita `activities.is_automated` (AUT) y `actor_type`, `direction`, `activity_type` (FLD) |

Los campos pueden declarar su dominio (`values`, `nullable: false`). Un valor fuera de él, o un nulo donde no se permite, lanza `K_FIELD_VALUE`: la ejecución se detiene en lugar de dejar entrar un registro en una población sin avisar.

## 4. Orden de decisión y motivos

1. Se resuelven todos los campos que lee el KPI (los suyos y los de todas las poblaciones de las que parte). Si falta alguno, el KPI es `not_available` con los motivos unidos en orden de aparición y la **lista exacta de campos que faltan**: `FLD`, `HM`, `HF`, `AUT`, `APT` (por ejemplo, `FLD+AUT`).
2. Si no falta ninguno, se calcula la operación.
3. Un resultado indefinido es `DEN0` (denominador cero, `missing: [nonzero_denominator]`) o `INSUF` (sin observaciones, `missing: [observations]`). `ORD` (orden de eventos indeterminado) existe en el catálogo, pero ningún KPI de F3.0 depende del orden.
4. Un cero real (numerador 0 sobre un denominador positivo, o un conteo de 0) es un 0 disponible.

Un resultado `not_available` es exactamente `{id, status, reason, missing}`; nunca lleva `value`, `numerator` ni `denominator`. Que un KPI no esté disponible nunca impide calcular los demás.

`FLD` (aprobado en F3.0) significa que la carga o el perfil no proporcionan un campo o atributo requerido. No cubre valores nulos en registros concretos: esos los tratan los filtros.

## 5. Contrato de los ratios

Se comprueba al cargar la configuración. Una infracción es un error de configuración y no se evalúa nada.

- Las dos poblaciones deben tener la **misma unidad** (`K_RATIO_UNIT`).
- `relation` es obligatorio (`K_RATIO_RELATION_MISSING`):

| relation | Requisito | Significado |
|---|---|---|
| `subset_of` | el numerador se define `from` el denominador | el numerador está contenido en el denominador (también se comprueba al ejecutar) |
| `same_base` | ambas se definen `from` la misma población base | filtros distintos sobre una misma base; el numerador no tiene por qué ser subconjunto; el valor puede superar 1 |
| `independent_allowed` | una `justification` escrita (`K_RATIO_JUSTIFICATION`) | bases distintas con la misma unidad |

Una relación que no coincide con cómo están definidas las poblaciones da `K_RATIO_RELATION`. No se presupone que un ratio sea una conversión de funnel. `forms_over_interviews_held` es `same_base` (ambas desde `mature`): su definición de F0 no exige que quien tiene formulario haya tenido entrevista, aunque en los datos generados se cumpla. Los ejemplos válidos y no válidos se prueban en `tests/test_kpi_spec_schema.py`.

## 6. Elegibilidad (regla del perfil de admisiones)

F0 define un lead elegible como `is_duplicate = false` e `is_reactivation = false`. El mapeo de admisiones asigna `record_origin = duplicate` cuando `is_duplicate`, `reactivation` cuando `is_reactivation` y `original` en otro caso, y rechaza las filas con ambos indicadores (`M_ORIGIN_CONFLICT`). Por tanto, **en el perfil de admisiones**:

`record_origin = original` ⇔ `is_duplicate = false` e `is_reactivation = false`.

Es una regla del perfil de admisiones (la población `eligible` de `profiles/admissions/kpis.yaml`), no del motor, que no sabe nada de elegibilidad. `tests/test_kpi_eligibility.py` comprueba la equivalencia con los datos generados (frente al cargador de F0), por el camino canónico (dataframes del adaptador) y en el fixture. `record_origin` se declara con su dominio y como no nulo:
- un origen desconocido lo rechazan el contrato (`E_ENUM`) y el motor (`K_FIELD_VALUE`);
- un origen nulo lanza `K_FIELD_VALUE`;
- si falta el campo de origen, todos los KPIs salen `FLD`.

Ningún registro entra en `eligible` sin avisar.

## 7. Los ocho KPIs de F3.0

| KPI | Operación | Unidad | Población | Requiere |
|---|---|---|---|---|
| `eligible_leads` | count | lead | elegibles | `record_origin` |
| `share_manual_route` | share | lead | elegibles | + `entry_route` |
| `main_kpi_interviews_held_over_opportunities` | share | lead | maduros (madurez) | `record_origin`, `created_at`, `snapshot_at`, `held_entered_at` (HM) |
| `show_rate_per_appointment` | share | cita | citas elegibles realizadas + no-show | campos de cita (APT), `snapshot_at` |
| `forms_over_interviews_held` | ratio `same_base` | lead | maduros con formulario / maduros con entrevista realizada | + `form_entered_at`, `held_entered_at` (HM) |
| `sla_first_attempt_24h_manual_weekend` | share (SLA, calendario) | lead | manuales, ventana de 24 h, sábado y domingo | + `entry_route`, `first_human_attempt_at` (AUT) |
| `first_response_p90_hours` | duration_stat p90 | lead | manuales, ventana de 24 h | + `first_human_attempt_at` (AUT) |
| `sales_cycle_median_days` | duration_stat mediana | lead | maduros matriculados | `record_origin`, `created_at`, `snapshot_at`, `won_at` |

Con los datos generados, los ocho son idénticos a F0, F1, F2 y `src/metrics.py` (valores a 6 decimales, numeradores, denominadores y campos descriptivos; `tests/test_kpi_regression.py`). En el fixture oficial de 12 registros:

| Variante | disponibles / no disponibles | no disponibles |
|---|---|---|
| `v_full` | 8 / 0 | — |
| `v_milestone` | 8 / 0 | — |
| `v_snapshot` | 6 / 2 | KPI principal, formularios / entrevistas (HM) |
| `v_no_automated` | 6 / 2 | SLA de fin de semana, p90 de primera respuesta (AUT) |
| `v_no_appointments` | 7 / 1 | show rate por cita (APT) |

## 8. Límites

- `time_model` solo admite `naive_wall_clock`. Los instantes UTC y las reglas de calendario local llegan con **F3.5**, que está planificada y no implementada.
- Solo está configurado el perfil de admisiones con sus ocho KPIs. Los otros 27 KPIs parametrizables son F3.1 (todavía no autorizada), y 12 KPIs siguen siendo funciones del perfil en `src/metrics.py`.
- Sin desgloses por cohorte, mes o segmento: los sigue produciendo `src/metrics.py`, que continúa siendo la referencia oficial.
- No se afirma preparación para datos reales ni para conexiones CRM.

## 9. Cómo ejecutar

```bash
pytest -q tests/test_kpi_*.py tests/test_regression_f2.py
python scripts/f3_run.py --check     # ejecución limpia, F0/F1/F2 congelados, ocho KPIs frente a las referencias, cinco variantes, manifiesto F3
```
