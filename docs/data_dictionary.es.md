**Idioma:** [English](data_dictionary.md) | Español

# Diccionario de datos (v1)

> Todos los archivos son **sintéticos**. Los identificadores (`lead_id`, `person_key`, `ADV_0x`, `PRG_x`) son inventados; el dataset no contiene nombres, emails, teléfonos ni registros reales. Los timestamps son locales, sin zona horaria, truncados al segundo.

Archivos: `data/leads.csv` (una fila por lead-deal, foto a `snapshot_date`), `data/activities.csv` (una fila por actividad), `data/dq_ground_truth.csv` (ayuda de validación con las anomalías inyectadas).

## 1. `leads.csv`

### 1.1 Identidad y captación

| Columna | Tipo | Valores permitidos / regla |
|---|---|---|
| `lead_id` | texto | `L000001`…; único; ordenado por `created_at` |
| `person_key` | texto | `P000001`…; presente en todas las filas; enlaza duplicados y reactivaciones con la misma persona sintética (§2.4 de supuestos) |
| `is_reactivation` | bool | true si la fila procede de nurture; se reporta aparte y nunca cuenta como lead nuevo |
| `reactivated_from_lead_id` | texto | deal de origen (cerrado por `future_intake`, en nurture); nulo en el resto |
| `is_duplicate` | bool | true si la fila cumple la regla de duplicado: no es reactivación y existe una fila anterior no duplicada de la misma persona creada ≤ 14 días antes |
| `is_synthetic` | bool | siempre true |
| `created_at` | fecha-hora | entrada del lead |
| `source` | texto | subfuente dentro del canal (p. ej. `webinar_live`) |
| `channel_group` | texto | `paid_social`, `webinar`, `web_direct`, `organic`, `referral`, `event`, `partner` |
| `program_alias` | texto | `PRG_A`, `PRG_B` (orientados a sanitario), `PRG_C`, `PRG_D` (orientados a no sanitario) |
| `candidate_profile` | texto | `healthcare` (sanitario), `non_healthcare` (no sanitario) |
| `entry_path` | texto | `bot_booked` (el bot agendó al entrar) o `manual` (Opportunity, seguimiento del asesor); nulo en duplicados |

### 1.2 Propiedad y contacto

| Columna | Tipo | Regla |
|---|---|---|
| `first_owner_id` | texto | asesor asignado al entrar (`ADV_01`…`ADV_05`) |
| `current_owner_id` | texto | owner en la fecha de corte; solo difiere del primero tras una reasignación |
| `reassigned_flag`, `reassigned_at` | bool, fecha-hora | reasignación por SLA (ruta manual), a partir de 24 horas naturales |
| `first_human_attempt_at` | fecha-hora | primera llamada o WhatsApp saliente del asesor no automatizado |
| `first_connected_at` | fecha-hora | primera llamada conectada, respuesta entrante del candidato o entrevista realizada |

### 1.3 Etapas y estados

| Columna | Tipo | Regla |
|---|---|---|
| `entered_opportunity_at` | fecha-hora | solo ruta manual (nulo en la ruta bot) |
| `entered_interview_booked_at` | fecha-hora | primera reserva (`activity_at` de la primera fila de entrevista) |
| `entered_interview_held_at` | fecha-hora | primera cita `held` (su `interview_scheduled_for`) |
| `entered_form_completed_at`, `entered_enrollment_link_sent_at` | fecha-hora | hitos |
| `enrolled_at` | fecha-hora | cerrado ganado (pago confirmado) |
| `closed_lost_at` | fecha-hora | cerrado perdido |
| `pipeline_stage` | texto | `new_lead`, `opportunity`, `interview_booked`, `interview_held`, `form_completed`, `enrollment_link_sent`, `closed_won`, `closed_lost` — última etapa alcanzada en la fecha de corte |
| `lead_status` | texto | `new`, `working`, `iloc_sequence`, `nurture`, `closed_won`, `closed_lost` (significado en supuestos §2.1) |
| `last_interview_outcome` | texto | resultado de la última cita no reemplazada: `pending`, `held`, `no_show`, `cancelled`; nunca `rescheduled`; nulo si no hay citas |
| `lost_reason` | texto | `iloc`, `financial`, `official_qualification`, `future_intake`; nulo si no está perdido, o nulo deliberado en una fila `closed_lost` (anomalía) |

Las reglas de consistencia R1–R13 están en la §2.1 de supuestos y las verifica `tests/test_integrity.py`.

### 1.4 ILOC y nurture

| Columna | Tipo | Regla |
|---|---|---|
| `iloc_started_at` | fecha-hora | activación del último episodio ILOC iniciado antes del corte (WhatsApp + email 1 de BD0) |
| `iloc_ended_at`, `iloc_end_reason` | fecha-hora, texto | `responded`, `booked`, `closed_iloc`; nulo mientras el episodio está activo |
| `iloc_episode_count` | entero | episodios ILOC iniciados antes del corte (inicial y/o tras no-show) |
| `nurture_started_at` | fecha-hora | = `closed_lost_at` en deals `future_intake` que entran en nurture |
| `nurture_ended_at`, `nurture_end_reason` | fecha-hora, texto | `reactivated` (= `created_at` del lead reactivado) o `window_ended` (150 días); nulo mientras sigue en nurture |

### 1.5 Gobernanza, campos postentrevista y precio

| Columna | Tipo | Regla |
|---|---|---|
| `has_open_task`, `next_task_due_at` | bool, fecha-hora | derivados de tareas con estado `open` u `overdue` |
| `candidate_situation` | texto | `employed`, `unemployed`, `student`, `career_change` |
| `immediate_interest`, `program_interest` | texto | `high`, `medium`, `low` |
| `decision_maker` | texto | `self`, `shared`, `other` |
| `main_objection` | texto | `price`, `time`, `official_qualification`, `timing`, `none` |
| `payment_preference` | texto | `single`, `installments`, `undecided` |
| `next_step_agreed` | bool | efecto programado nulo sobre la conversión |
| `payment_type` | texto | `single` (pago único), `installments` (fraccionado) — solo cerrados ganados |
| `list_price` | decimal | 3.200 |
| `campaign_discount` | decimal | 600, 500 o 350 (sorteo aleatorio; escenario arbitrario) |
| `one_time_discount` | decimal | pago único: (3.200 − descuento de campaña) × 0,15; fraccionado: 0 |
| `net_price` | decimal | lista − descuento de campaña − descuento de pago único |
| `snapshot_date` | fecha-hora | 2025-12-31 23:59:00 |

Los siete campos postentrevista solo se rellenan tras una entrevista realizada; en torno al 10 % de los entrevistados tiene al menos un campo vacío (anomalía).

## 2. `activities.csv`

| Columna | Tipo | Valores permitidos / regla |
|---|---|---|
| `activity_id` | texto | `A0000001`…; ordenado por `activity_at` |
| `lead_id` | texto | debe existir en `leads.csv`; los duplicados no tienen actividades |
| `activity_at` | fecha-hora | momento de la actividad (en entrevistas: cuándo se reservó la cita; en tareas: cuándo se creó) |
| `actor_type` | texto | `advisor`, `bot`, `system`, `candidate` (respuestas entrantes) |
| `actor_id` | texto | asesor que la realizó; nulo para bot, sistema y candidato |
| `activity_type` | texto | `call`, `whatsapp`, `email`, `interview`, `task`, `note` |
| `direction` | texto | `outbound`, `inbound`, `internal` (entrevistas, tareas, notas) |
| `is_automated` | bool | mensajes de plantilla o del bot (emails de secuencia, recordatorios); las llamadas y WhatsApps manuales del asesor son false |
| `sequence_name` | texto | `booking`, `first_contact`, `iloc`, `reschedule`, `pre_interview_reminder`, `post_interview`, `form_reminder`, `form`, `enrollment`, `nurture`, `none` |
| `sequence_step` | texto | p. ej. `BD0`, `BD2_call_task`, `reminder_24h`, `personal_whatsapp`, `nurture_email_2`, `closed_lost` |
| `sequence_instance` | entero | número de episodio ILOC dentro del lead |
| `business_day_index` | entero | solo ILOC: 0, 2, 3, 4, 5 (acciones), 6 (nota de cierre); nunca 1 |
| `call_outcome` | texto | `connected`, `no_answer`, `voicemail`, `wrong_number` |
| `email_status` | texto | `sent`, `not_sent`, `failed` (fallos solo en nurture) |
| `interview_scheduled_for` | fecha-hora | hora de la cita |
| `interview_outcome` | texto | `pending` (cita posterior al corte), `held`, `no_show`, `rescheduled` (reemplazada, no terminal), `cancelled` |
| `interviewer_id` | texto | owner en el momento de la cita |
| `rescheduled_from_activity_id` / `replaced_by_activity_id` | texto | cadena de reprogramación (cita de reemplazo ↔ cita reemplazada) |
| `rebooked_after_activity_id` | texto | nueva reserva tras una cita `no_show` o `cancelled` (no es un reemplazo) |
| `task_due_at`, `task_completed_at` | fecha-hora | solo tareas |
| `task_status` | texto | `open`, `overdue` (vencida antes del corte, no realizada), `done`, `cancelled` (secuencia detenida) |

## 3. `dq_ground_truth.csv` (ayuda de validación)

| Columna | Significado |
|---|---|
| `lead_id` | lead afectado |
| `issue_type` | `duplicate`, `missing_lost_reason`, `untouched_manual`, `open_without_task`, `overdue_task`, `stage_support_omitted`, `empty_post_interview_fields`, `stalled` |
| `detail` | etapa o campos implicados; en `overdue_task`: `injected` o `stalled_lead` |

Las pruebas comparan cada regla de detección con este archivo en la misma unidad (lead, o lead + etapa en `stage_support_omitted`). Una detección fuera del conjunto inyectado, o un caso inyectado que la regla puede observar y no detecta, es un error de lógica. Los casos inyectados que la regla aún no puede observar en la fecha de corte (leads sin tocar o estancados recientes) se cuentan aparte.
