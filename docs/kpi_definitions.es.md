**Idioma:** [English](kpi_definitions.md) | Español

# Definiciones de KPIs (v1)

> Son **definiciones analíticas del proyecto**, no KPIs históricos oficiales. Todos los valores calculados con ellas en este repositorio son sintéticos.

## 0. Convenciones

| Término | Definición |
|---|---|
| Lead elegible | `is_duplicate = false` e `is_reactivation = false`. Los reactivados se reportan aparte |
| Lead maduro | `snapshot_date − created_at ≥ 60 días` (timestamps completos) |
| Cohorte | mes de `created_at`. Etiqueta calculada con la proporción de leads elegibles maduros: `mature`/madura (100 %), `partial`/parcial (una parte), `immature`/inmadura (ninguno). Las conversiones de cohorte usan solo leads maduros; las cohortes parciales muestran la proporción incluida y no se comparan con las maduras |
| Periodo | mes del timestamp del evento (actividad, hora de la cita, matrícula); se usa para actividad, carga, show rate y gobernanza |
| Cita elegible | cita de un lead elegible, no reemplazada por reprogramación (`replaced_by_activity_id` nulo) y con `interview_scheduled_for` ≤ `snapshot_date` |
| Lead abierto | `pipeline_stage` distinto de `closed_won` y `closed_lost` en la fecha de corte |

## 1. KPI principal y métricas de entrevista

| KPI | Unidad | Numerador | Denominador | Base |
|---|---|---|---|---|
| **Entrevistas realizadas / oportunidades (KPI principal)** | lead | leads elegibles maduros con ≥ 1 cita `held` | **todos** los leads elegibles maduros, ambas rutas | cohorte |
| Conversión a entrevista realizada, ruta manual | lead | lo mismo, `entry_path = manual` | leads elegibles maduros de la ruta manual | cohorte |
| Conversión a entrevista realizada, ruta bot | lead | lo mismo, `entry_path = bot_booked` | leads elegibles maduros de la ruta bot | cohorte |
| Booking rate | lead | leads elegibles maduros con `entered_interview_booked_at` | leads elegibles maduros | cohorte |
| **Show rate por cita** | cita | citas elegibles `held` | citas elegibles `held` + `no_show` | mes de `interview_scheduled_for` |
| Show rate por lead | lead | leads con ≥ 1 cita elegible `held` | leads con ≥ 1 cita elegible `held` o `no_show` (cohortes maduras) | cohorte |
| Tasa de cancelación | cita | citas elegibles `cancelled` | citas elegibles `held`, `no_show` o `cancelled` | mes de `interview_scheduled_for` |

En el KPI principal, "oportunidades" significa todos los leads entrantes elegibles. Nunca se usa solo la etapa Opportunity como denominador, porque dejaría fuera la ruta bot. Los resultados de citas nunca se usan como conteos de leads.

## 2. Funnel (cohortes maduras)

| KPI | Numerador | Denominador |
|---|---|---|
| Formularios completados / entrevistas realizadas | leads con `entered_form_completed_at` | leads con `entered_interview_held_at` |
| Matrículas / entrevistas realizadas | leads con `enrolled_at` | leads con `entered_interview_held_at` |
| Enlaces / formularios | leads con `entered_enrollment_link_sent_at` | leads con `entered_form_completed_at` |
| Matrículas / leads elegibles | leads con `enrolled_at` | leads elegibles maduros |
| Ciclo de venta | mediana y media de `enrolled_at − created_at`, en días | leads maduros matriculados |

## 3. Entrada y SLA (definición analítica del proyecto)

| KPI | Numerador | Denominador |
|---|---|---|
| Proporción por ruta | leads elegibles por `entry_path` | leads elegibles |
| Contactados (manual) | leads manuales con `first_human_attempt_at` | leads manuales elegibles |
| Sin tocar (manual) | leads manuales abiertos sin intento humano en la fecha de corte | leads manuales elegibles abiertos |
| Primer intento ≤ 24 h (manual) | `first_human_attempt_at − created_at` ≤ 24 horas naturales | leads manuales creados ≥ 24 h antes del corte (ventana completa) |
| Primer intento el mismo día (manual) | primer intento en la fecha natural de `created_at` | mismo denominador |
| Primera respuesta, mediana y p90 | `first_human_attempt_at − created_at` en horas naturales | leads manuales con intento (misma ventana) |
| Tasa de contacto | leads con `first_connected_at` | leads con ≥ 1 intento humano |
| Tasa de reasignación | leads manuales con `reassigned_flag` | leads manuales elegibles |
| Ruta bot: confirmación preentrevista | leads de ruta bot con confirmación o recordatorio del bot antes de la primera cita | leads elegibles de ruta bot |
| Ruta bot: contacto humano preentrevista | leads de ruta bot con actividad manual del asesor antes de la primera cita | leads elegibles de ruta bot |

La primera respuesta se mide en **horas naturales** (decisión documentada de v1). Las horas naturales incluyen noches y fines de semana, en los que los asesores del escenario (lunes–viernes 09–19) no trabajan, así que esta definición puede penalizar a los leads que entran fuera de horario. El notebook muestra por separado el SLA observado de las entradas entre semana y en fin de semana; la división describe el escenario y no demuestra que todos los leads de fin de semana incumplan.

## 4. Fuentes, perfiles y programas (cohortes maduras)

Para cada segmento: leads, realizadas / leads, matriculados / leads, matriculados / realizadas, proporción ILOC (perdidos por `iloc` / leads), € netos por lead (Σ `net_price` / leads). Las diferencias reproducen los modificadores del escenario.

## 5. Asesores (exploratorio)

| Indicador | Definición |
|---|---|
| Carga | leads elegibles por `first_owner_id` y mes de `created_at`; reactivados aparte; sin duplicados |
| Carga esperada | volumen mensual del escenario × peso de asignación (antes del azar) |
| Bandas | < 100, 100–120 habitual, 121–150 alta, > 150 alerta |
| Conversión | realizadas / leads y matriculados / leads por `first_owner_id` y por `current_owner_id`, con n e intervalo de Wilson al 95 % |
| Actividad | actividades atribuidas a `actor_id` (quien las realizó) |

Los asesores comparten los mismos parámetros base: las diferencias no se atribuyen a desempeño individual.

## 6. Pérdidas y nurture

| KPI | Numerador | Denominador |
|---|---|---|
| Distribución de motivos de pérdida | cerrados perdidos por motivo | cerrados perdidos con motivo |
| Motivos por punto de salida | tabla cruzada motivo × última etapa alcanzada antes del cierre | — |
| Reactivación | deals de nurture terminados como `reactivated` | deals de nurture con la ventana de 150 días completa en la fecha de corte |
| Fallos de email de nurture | emails de nurture `not_sent` o `failed` | emails de nurture programados |

## 7. Gobernanza CRM (en la fecha de corte)

| Indicador | Numerador | Denominador |
|---|---|---|
| Abiertos sin próxima tarea | leads abiertos con `has_open_task = false` | leads elegibles abiertos |
| Abiertos con tarea vencida | leads abiertos con ≥ 1 tarea `overdue` | leads elegibles abiertos |
| Seguimiento manual del asesor en 48 h | leads elegibles con ≥ 1 actividad del asesor `outbound`, de tipo `call` o `whatsapp` y no automatizada, en la ventana (primera entrevista realizada, primera entrevista realizada + 48 horas naturales]; no se excluyen los fines de semana; las actividades anteriores a la entrevista nunca cuentan | leads elegibles cuya primera entrevista realizada es ≥ 48 h anterior al corte |
| Cerrados perdidos sin motivo | `closed_lost` con `lost_reason` nulo | cerrados perdidos |
| Campos postentrevista incompletos | entrevistados con ≥ 1 campo postentrevista nulo | entrevistados |
| Cambio de etapa sin su registro de soporte | eventos de etapa sin su registro dedicado en el mismo timestamp (regla de calidad de datos, conciliada con la verdad de referencia) | eventos de etapa omitibles (opportunity, form_completed, closed_lost) |
| Cambio de etapa sin actividad en ± 24 h | eventos de etapa sin ninguna actividad del lead en ± 24 h (vista de gobernanza menos estricta; subconjunto de la fila anterior) | todos los eventos de etapa |
| Duplicados | `is_duplicate = true` | todas las filas |

## 8. Finanzas (leads matriculados, vista de periodo)

Valor bruto de lista Σ `list_price`; descuento de campaña Σ `campaign_discount`; descuento de pago único Σ `one_time_discount`; precio neto Σ y media de `net_price`, global y por `payment_type`; mezcla de modalidad de pago. Sin pagos, cobros, CAC ni ROI en v1.
