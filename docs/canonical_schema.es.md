**Idioma:** [English](canonical_schema.md) | Español

# Esquema CRM canónico `crm-canonical/0.1.1` (F2)

> Todos los datos del proyecto son **sintéticos**. F2 añade una representación canónica, basada en archivos, de los datos de admisiones y una ruta validada desde ella hasta el código de métricas existente. No se conecta a ningún CRM, no lee datos reales, no añade ninguna aplicación y no afirma que el esquema sirva para otros funnels. Solo existe el perfil de admisiones. La portabilidad tendría que probarse en una fase posterior.

## 1. Por qué y qué

Antes de F2, `src/metrics.py` leía directamente los dos CSV de admisiones. F2 coloca un contrato neutral en medio:

```
data/leads.csv + data/activities.csv
   └─ src/canonical/mapping.py          (profiles/admissions/mapping_csv_v1.yaml)
        └─ tablas canónicas              (schema/canonical_v0.1.1.yaml, validadas por src/canonical/validate.py)
             └─ src/canonical/adapters/admissions.py   (profiles/admissions/rules.yaml, kpi_requirements.yaml)
                  └─ src/metrics.py (F1 + corrección de robustez autorizada v1.2.1-f2)  +  src/canonical/history.py
```

El adaptador de admisiones reconstruye exactamente los dataframes que lee `metrics.py`. Por eso las 47 métricas de referencia calculadas por la ruta canónica son idénticas a F0 y F1. Las pruebas lo comprueban métrica a métrica.

## 2. Tablas

Un CSV por tabla (UTF-8, fila de cabecera, celda vacía = nulo). La lista completa de columnas, tipos y nulabilidad está en [`schema/canonical_v0.1.1.yaml`](../schema/canonical_v0.1.1.yaml), revisión aditiva de [`schema/canonical_v0.1.yaml`](../schema/canonical_v0.1.yaml) (que se conserva sin cambios). Los datasets pueden declarar `crm-canonical/0.1` o `crm-canonical/0.1.1`; solo los 0.1.1 pueden llevar `stage_events.seq`.

| Tabla | Obligatoria | Clave | Contenido |
|---|---|---|---|
| `dataset` | sí (1 fila) | `dataset_id` | versión del esquema, perfil, prefijo de atributos, `data_origin`, `history_mode`, `timestamp_mode`, `source_timezone`, `snapshot_at`, moneda |
| `records` | sí | `record_id` | una fila por registro (lead-deal): origen (`original` / `duplicate` / `reactivation`), padre, creación, ruta, fuente, canal, producto, propietarios, reasignación, **estado en la fecha de corte** (`current_stage`, `current_status`, `lost_reason`, `won_at`, `lost_at`), importes |
| `stage_events` | no | `event_id` | historial de etapas; `event_kind` = `transition`, `first_entry_milestone` o `reopen`; `seq` opcional = orden de la fuente dentro del registro (0.1.1) |
| `activities` | sí | `activity_id` | llamadas, mensajes, emails, tareas, notas; `is_automated` es una columna opcional de **capacidad** |
| `appointments` | no (capacidad) | `appointment_id` | reserva, franja, resultado (`pending`, `held`, `no_show`, `rescheduled`, `cancelled`), cadenas de reprogramación y nueva reserva |
| `record_attributes` | no | (`record_id`, `attribute`) | atributos del perfil en formato largo con `value_type`; cada clave empieza por el prefijo del dataset (`adm_`) |

Solo se admiten columnas de extensión en `records`, `activities` y `appointments`, y siempre con el prefijo del dataset (`adm_…`). Cualquier otra columna no declarada se rechaza.

## 3. Modos de historial: nunca se deduce historial

| `history_mode` | `event_kind` permitidos | Qué se puede medir |
|---|---|---|
| `full_event_history` | `transition`, `reopen` | primeras entradas, reentradas, retrocesos, reaperturas, tiempo en etapa |
| `milestone_first_entry` | `first_entry_milestone` | solo la primera entrada en cada etapa |
| `snapshot_only` | ninguno | solo el estado en la fecha de corte |

Los eventos de etapa nunca se deducen de `current_stage`, de las citas ni de las actividades. Un dataset de hitos conserva `event_kind = first_entry_milestone` y nunca produce conteos de entradas, retrocesos, reaperturas ni duraciones. En `snapshot_only` no existe ningún hito; los campos de estado (`won_at`, `lost_at`) siguen siendo utilizables como estado, no como historial.

El CSV de admisiones generado solo contiene timestamps de primera entrada (`entered_*_at`, `enrolled_at`, `closed_lost_at`). Por eso se mapea como `milestone_first_entry`.

## 4. Timestamps

| `timestamp_mode` | Se guarda como | Permitido para |
|---|---|---|
| `naive_wall_clock` | `YYYY-MM-DD HH:MM:SS`, hora local; `source_timezone` es solo metadato | solo `data_origin` = `synthetic` o `legacy` |
| `utc` | `YYYY-MM-DDTHH:MM:SSZ` | cualquier origen |

En modo `utc`, los valores con desfase se convierten a UTC. Los valores sin zona se localizan con `source_timezone`. Una hora local **ambigua** (hora repetida) o **inexistente** (hora saltada) es un error, nunca una suposición. El dataset de admisiones es sintético y usa `naive_wall_clock` (Europe/Madrid como metadato). En F2, el adaptador de admisiones solo acepta `naive_wall_clock`, porque sus definiciones de SLA entre semana y en el mismo día usan la hora local.

## 5. Reglas del contrato (neutrales)

| Regla | Comprobación |
|---|---|
| C01 | `event_kind` permitido por `history_mode`; `snapshot_only` no tiene eventos de etapa |
| C02 | como máximo un `first_entry_milestone` por registro y etapa |
| C03 | `transition` y `reopen` tienen `from_stage`; `first_entry_milestone` no tiene |
| C04 | los timestamps siguen `timestamp_mode`; `naive_wall_clock` solo para datos sintéticos o legacy |
| C05 | ningún evento de etapa, actividad ni reserva posterior a `snapshot_at` |
| C06 | `replaced_by_appointment_id` informado exactamente cuando el resultado es `rescheduled`, recíproco con `rescheduled_from_appointment_id` |
| C07 | `is_automated` y `booking_is_automated` presentes en ambas tablas o en ninguna |
| C08 (0.1.1) | `stage_events.seq`, si existe, es único por registro y no contradice a `occurred_at` |
| C09 (0.1.1) | orden dentro de un registro: `seq` si existe; si no, `occurred_at`; timestamps iguales sin `seq` = orden indeterminado (§11.4) |

El validador comprueba además la versión del esquema, tablas, columnas, nulabilidad, tipos, enumeraciones, patrones, claves primarias y claves foráneas. Es código propio, sin dependencias nuevas. Los errores tienen códigos estables (`E_…`).

## 6. Perfil de admisiones

### 6.1 Mapeo (`profiles/admissions/mapping_csv_v1.yaml`)

| CSV | Canónico |
|---|---|
| `lead_id`, `person_key`, `created_at`, `source`, `channel_group`, `program_alias`, `entry_path`, propietarios, `reassigned_at`, `pipeline_stage`, `lead_status`, `lost_reason`, `enrolled_at`, `closed_lost_at`, `list_price`, `net_price` | `records` (uno a uno) |
| `is_duplicate`, `is_reactivation` | `records.record_origin` (ambos verdaderos = error) |
| `reactivated_from_lead_id` | `records.parent_record_id` |
| `campaign_discount` + `one_time_discount` | `records.discount_amount` (agregado) **y** `adm_campaign_discount`, `adm_one_time_discount` (por separado) |
| `entered_*_at`, `enrolled_at`, `closed_lost_at` | `stage_events` (`first_entry_milestone`) |
| ILOC, nurture, campos post-entrevista, `payment_type`, `last_interview_outcome`, `candidate_profile` | `record_attributes` (`adm_…`) |
| filas de actividad con `activity_type = interview` | `appointments` (`direction = internal` y `sequence_name = booking` son constantes que se comprueban) |
| resto de filas de actividad | `activities` (`sequence_instance`, `business_day_index` como extensiones `adm_`) |
| `is_synthetic`, `snapshot_date` | `dataset.data_origin`, `dataset.snapshot_at` |
| `first_human_attempt_at`, `first_connected_at`, `has_open_task`, `next_task_due_at`, `reassigned_flag` | no se mapean: el adaptador los recalcula con las reglas de F0 (§6.3) |

### 6.2 Reglas del perfil (`profiles/admissions/rules.yaml`)

Estas reglas pertenecen al perfil de admisiones, no al contrato neutral. Sus códigos de error son `P_…`.

| Regla | Comprobación |
|---|---|
| P01 | las etapas son las del perfil (`new_lead` … `enrollment_link_sent`, `closed_won`, `closed_lost`) |
| P02 | `entry_route` es `bot_booked` o `manual` (los duplicados pueden no tenerla) |
| P03 | una reactivación tiene `parent_record_id` |
| P04 | el padre existe, tiene la misma `person_key`, se creó antes y está `closed_lost` con `future_intake` |
| P05 | los originales y los duplicados no tienen padre |
| P06 | `won_at` si y solo si `closed_won`; `lost_at` si y solo si `closed_lost` |
| P07 | importes todos informados o todos nulos; lista − descuento = neto (al céntimo) |
| P08 | `adm_campaign_discount` + `adm_one_time_discount` = `discount_amount` (al céntimo) |
| P09 | `lost_reason` es un motivo del perfil, en un registro `closed_lost` |
| P10 | `current_status` es un estado del perfil |

### 6.3 Adaptador (`src/canonical/adapters/admissions.py`)

El adaptador reconstruye los dataframes `leads` y `activities` con las mismas columnas y tipos que `checks.load`. Con los datos generados, el viaje de ida y vuelta es exacto (probado columna a columna). Los campos derivados siguen las reglas de F0:

| Campo | Regla |
|---|---|
| `first_human_attempt_at` | primera llamada o WhatsApp saliente del asesor con `is_automated = False` |
| `first_connected_at` | primera llamada conectada, actividad entrante o cita realizada (su franja) |
| `has_open_task`, `next_task_due_at` | tareas en estado `open` / `overdue`; vencimiento más próximo |
| `entered_<stage>_at` | primera entrada, solo a partir de eventos de etapa |
| `enrolled_at`, `closed_lost_at` | `records.won_at`, `records.lost_at` (estado) |

Si falta una capacidad, las columnas que dependen de ella quedan vacías. Todos los KPIs que las necesitan se informan como no disponibles (§7), así que del adaptador no sale ningún número calculado con entradas ausentes.

## 7. Disponibilidad de KPIs (`profiles/admissions/kpi_requirements.yaml`)

| Requisito | Se cumple cuando | Código de motivo si falta |
|---|---|---|
| `stage_milestones` | `full_event_history` o `milestone_first_entry` | HM |
| `stage_transitions` | `full_event_history` | HF |
| `is_automated` | existe `activities.is_automated` | AUT |
| `appointments` | existe la tabla `appointments` | APT |

Un KPI no disponible se devuelve como `{"id", "status": "not_available", "reason", "missing"}` **sin** las claves `value`, `numerator` ni `denominator`, de modo que nunca puede leerse como cero. Si faltan varios requisitos, los motivos se unen (por ejemplo, `HM+AUT`).

Desde v1.2.1-f2 se distinguen tres situaciones, en este orden:

| Situación | Motivo | Ejemplo |
|---|---|---|
| módulo ausente (falta una tabla o columna que el KPI necesita) | `HM`, `HF`, `AUT`, `APT` | SLA sin `is_automated` → `AUT`, aunque `metrics.py` calcularía 0 |
| denominador cero (hay entradas, pero el denominador es 0) | `DEN0` (`missing: [nonzero_denominator]`) | formularios / entrevistas realizadas cuando ningún lead tiene entrevista realizada |
| datos insuficientes (una mediana, media o percentil sin observaciones) | `INSUF` (`missing: [observations]`) | ciclo de venta cuando ningún lead maduro se ha matriculado |

Un cero real (numerador 0 sobre un denominador positivo) sigue siendo un valor disponible de 0. Que un KPI no esté disponible nunca impide calcular los demás.

El catálogo de F2 tiene 31 indicadores: 24 métricas y 7 indicadores de historial (`first_entry`, `entry_count`, `regression_events`, `regression_rate`, `reopen_events`, `reopen_rate` y `time_in_stage`, una capacidad sin valor esperado en el fixture). También se declaran los requisitos de las 47 métricas de referencia.

| Variante del fixture a mano | disponibles | no disponibles |
|---|---|---|
| `v_full` (historial completo, todas las tablas) | 31 | 0 |
| `v_milestone` | 25 | 6 (HF) |
| `v_snapshot` | 16 | 15 (9 HM, 6 HF) |
| `v_no_automated` | 23 | 8 (AUT) |
| `v_no_appointments` | 25 | 6 (APT) |

El dataset de admisiones generado se comporta como `v_milestone`: están disponibles las 24 métricas y `first_entry`, pero no los 6 indicadores HF.

## 8. Definiciones de historial (`src/canonical/history.py`)

Población: registros con `record_origin = original`.

| Indicador | Definición | Necesita |
|---|---|---|
| `first_entry` | registros con ≥ 1 entrada en cada etapa | hitos |
| `entry_count` | entradas en cada etapa, reentradas incluidas | historial completo |
| `regression_events` | transiciones entre etapas abiertas que retroceden | historial completo |
| `regression_rate` | transiciones de retroceso / todos los eventos de transición | historial completo |
| `reopen_events` | eventos de reapertura (etapa terminal → abierta) | historial completo |
| `reopen_rate` | registros con ≥ 1 reapertura / registros que alcanzaron una etapa terminal | historial completo |
| `time_in_stage` | mediana de horas entre la entrada en una etapa y el siguiente evento (la última etapa, hasta la fecha de corte) | historial completo |

## 9. Pruebas y fixtures

- `tests/fixtures/canonical_handcalc/`: fixture oficial de F2 desde v1.2.1-f2. Tiene **12 registros sintéticos construidos a mano** en cinco variantes, con `expected.json` calculado a mano (tablas de origen, derivaciones e inventario de cobertura). Sustituye al borrador anterior de 9 registros (R1–R9), que no se reproduce; no es el fixture aprobado en el plan. Se comprueba de tres formas: el test de esquema de lo esperado, un recálculo independiente que no usa ni el generador, ni el adaptador, ni `metrics.py`, y la ruta completa por el adaptador y `metrics.py` para **las cinco variantes**. Su procedencia, incluidas las fechas y citas cambiadas en v1.2.0-f2, queda registrada en `expected.json` (`provenance`).
- `tests/test_metrics_robustness.py` (v1.2.1-f2): denominadores cero, sin tabla de citas, sin citas desde el 2025-07-01, estadísticos sin observaciones, módulo ausente y la distinción DEN0 / INSUF / capacidad.
- `tests/fixtures/mapping_errors/`: un par de CSV válido de tres leads y 21 corrupciones, cada una con su código de error y su etapa esperados (mapeo, contrato o perfil).
- `tests/fixtures/timezones/`: casos límite de cambio de hora en Europe/Madrid.
- `tests/test_regression_f1.py`: F0 y F1 idénticos byte a byte; las 47 métricas por la ruta canónica son iguales a F0 y F1.

## 10. Corrección de robustez en `src/metrics.py` (v1.2.1-f2, autorizada)

v1.2.0-f2 detectó que `src/metrics.py` lanzaba una excepción con tres tipos de entrada que nunca se dan en los datos generados. La corrección autorizada no cambia ninguna definición ni ningún valor:

| Defecto (v1.2.0-f2) | Entrada | Corrección |
|---|---|---|
| MP1 `ZeroDivisionError` en `forms_over_interviews_held` (dos enteros de Python); posible `inf` en otras razones | ningún lead maduro con entrevista realizada | todas las razones de `baseline_metrics` y `directional_rates` pasan por `rate()` → NaN, informado como DEN0 |
| MP3 `TypeError` en `Context.bot_pre` (`Series.map` con un mapa de fechas vacío lo convierte a float) | ninguna fila de citas | búsqueda con `reindex`, que conserva el tipo fecha |
| MP3b `TypeError` en `show_rate_per_lead` (resultado vacío de tipo texto) | ninguna fila de citas | `Context.showlead` con tipo bool |
| MP4 `AttributeError` en `Context.personal_wa_appointments` (columna vacía de tipo object usada como máscara) | ninguna cita realizada / no-show desde el 2025-07-01 | columna booleana tipada |

Con los datos generados, el documento de métricas de F1 que genera **en memoria** el `metrics.py` corregido es idéntico byte a byte a `reports/f1/metrics_f1.json`; la comprobación nunca escribe en `reports/f1/` (está congelada y sus hashes se verifican antes y después de cada ejecución). Las 47 métricas son iguales a F0 y F1 por ambas rutas (probado). `src/metrics.py` se declara como la única modificación autorizada de un archivo fuente de F1; las pruebas de regresión fijan su nuevo hash.

## 11. Diferencias entre el plan aprobado y el contrato implementado

Esta revisión documenta las diferencias y solo añade la columna opcional `seq` (contrato `crm-canonical/0.1.1`, §11.4); nada más cambia en el contrato.

### 11.1 Registros

| Aprobado | Implementado | Qué conserva | Qué pierde o cambia |
|---|---|---|---|
| `is_duplicate` (indicador) | `record_origin` ∈ {`original`, `duplicate`, `reactivation`} con `parent_record_id` | el indicador de duplicado (`record_origin = duplicate` ⇔ `is_duplicate = true`) y el de reactivación en una sola columna; la vuelta a `is_duplicate` / `is_reactivation` es exacta (probado con los datos generados) | un registro no puede ser a la vez duplicado y reactivación (error de mapeo `M_ORIGIN_CONFLICT`); nunca ocurre en los datos generados, pero una fuente con indicadores solapados necesitaría dos columnas |
| `status` ∈ {open, won, lost} | `current_status` (estado operativo del perfil) **y** el resultado derivado de `current_stage` | ver §11.2 | `current_status` no es el `status` aprobado: es un campo distinto y más detallado |
| `closed_at` | `won_at` + `lost_at` | `closed_at` = `won_at` si `closed_won`, `lost_at` si `closed_lost` (la regla P06 garantiza exactamente uno, coherente con `current_stage`); la vuelta a `enrolled_at` / `closed_lost_at` es exacta | el tipo de cierre queda guardado dos veces (también en `current_stage`); ninguna de las dos formas conserva cierres anteriores de un registro reabierto, que solo existen en `stage_events` con historial completo |

### 11.2 `current_status` y el resultado abierto / ganado / perdido

`current_status` **no** es un cambio de nombre del `status = open / won / lost` aprobado. Conserva los estados operativos del perfil de admisiones en la fecha de corte: `new`, `working`, `iloc_sequence`, `nurture`, `closed_won` y `closed_lost` (regla P10). No son resultados: un lead en `nurture`, por ejemplo, es un deal ya cerrado como perdido (`current_stage = closed_lost`, `lost_reason = future_intake`) que sigue recibiendo mensajes de nurture.

El resultado se deriva de `current_stage` y de las etapas de ganado y perdido del perfil, nunca de `current_status` (`adapters/admissions.record_outcome`):

| `current_stage` | resultado |
|---|---|
| `closed_won` | ganado |
| `closed_lost` | perdido (sea cual sea el estado operativo, `nurture` incluido) |
| cualquier etapa abierta | abierto |

Es coherente con `won_at` / `lost_at` (P06). La prueba `tests/test_canonical_event_order.py` lo comprueba en el fixture y en los datos generados, donde todos los registros en `nurture` están perdidos.

### 11.3 `stage_events`: especificación aprobada y correspondencia

Especificación aprobada: clave (`record_id`, `seq`); obligatorios `record_id`, `seq`, `stage`, `entered_at`, `event_kind`; opcionales `exited_at`, `changed_by_type`; si dos eventos tienen el mismo timestamp, `seq` determina su orden.

| Aprobado | Implementado (0.1.1) | Nota |
|---|---|---|
| `record_id` | `record_id` | igual |
| `seq` (obligatorio, parte de la clave) | `seq` (**opcional**, único por registro cuando existe; regla C08) | se conserva cuando la fuente da un orden; el CSV de admisiones no lo da (solo timestamps de primera entrada), así que el mapeo no emite `seq` |
| clave (`record_id`, `seq`) | clave `event_id`; (`record_id`, `seq`) único cuando existe `seq` | `event_id` es un identificador adicional; en los hitos del CSV es `<record_id>:<etapa>` |
| `stage` | `to_stage` | la etapa en la que se entra |
| `entered_at` | `occurred_at` | cuándo se entró en la etapa |
| `event_kind` | `event_kind` ∈ {`transition`, `first_entry_milestone`, `reopen`} | igual |
| — | `from_stage` (transition / reopen) | adicional: cada evento indica la etapa que abandona, así que retrocesos y reaperturas se identifican evento a evento sin depender del orden |
| `exited_at` (opcional) | **no representado** | con historial completo y orden determinado equivale al `occurred_at` del siguiente evento del mismo registro; en `milestone_first_entry` es desconocido; no se guarda |
| `changed_by_type` (opcional) | **no representado** | se pierde quién o qué cambió la etapa; ningún KPI actual lo usa |

### 11.4 Orden de eventos (crm-canonical/0.1.1, reglas C08–C09)

- **Cuando la fuente da un orden**, se conserva en `seq`. `seq` es único por registro y no puede contradecir a `occurred_at` (un `seq` posterior nunca tiene un timestamp anterior). Los datasets que llevan `seq` declaran `crm-canonical/0.1.1`. Un dataset `crm-canonical/0.1` sigue siendo válido sin `seq`.
- **Sin `seq`**, los eventos siguen `occurred_at`. Los eventos de un mismo registro con el mismo `occurred_at` tienen un orden **indeterminado**. Nunca se resuelve por etapa, `event_id` ni posición en el archivo (v1.2.1-f2 usaba `event_id` para desempatar dentro de `time_in_stage`; se ha eliminado).
- **Qué depende del orden:** solo `time_in_stage`. Con orden indeterminado se devuelve como `not_available` con motivo `ORD` (`missing: [event_order]`). `first_entry`, `entry_count`, los retrocesos y las reaperturas no dependen del orden, porque cada evento lleva `from_stage` y `to_stage`. `tests/test_canonical_event_order.py` lo demuestra con eventos simultáneos, filas barajadas e ids renombrados.

## 12. Cómo ejecutar

```bash
python scripts/map_to_canonical.py      # escribe build/canonical/admissions/ (fuera del manifiesto)
pytest -q                               # todas las pruebas, F0/F1/F2
python scripts/f2_run.py --check        # ejecución limpia, F0/F1 congelados, 47 métricas, cinco variantes, manifiesto F2
```
