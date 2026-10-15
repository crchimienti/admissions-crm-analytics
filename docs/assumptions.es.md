**Idioma:** [English](assumptions.md) | Español

# Supuestos del proyecto (v1) — aprobados

> **Aviso.** Todos los datos de este proyecto son **sintéticos**. Ninguna cifra de este documento es una observación histórica ni un hallazgo. Los valores de la sección 3 son **parámetros del escenario sintético**: valores arbitrarios elegidos para que el escenario sea analizable, no tasas realistas, calibradas ni esperadas. Se guardan en una configuración central (`config/simulation_params.yaml`) y se generan con semilla fija (42).

## 0. Resumen de las cuatro categorías

| # | Categoría | Qué contiene | Origen | Cómo puede citarse |
|---|---|---|---|---|
| 1 | Contexto operativo proporcionado | Estructura del proceso, etapas, reglas CRM, cadencia ILOC, rangos orientativos | Experiencia profesional real, anonimizada | "El proceso se basa en una experiencia operativa real anonimizada" |
| 2 | Decisiones analíticas confirmadas | Definiciones de KPIs, cohortes, SLA, tratamiento de calendario y precios | Decisiones de diseño de este proyecto | "Definición analítica del proyecto", nunca "KPI oficial" |
| 3 | Parámetros del escenario sintético | Tasas, mezclas, tiempos, anomalías y probabilidades de descuento | Elegidos arbitrariamente para la simulación | "Parámetro del escenario sintético"; nunca como dato, tasa realista o resultado |
| 4 | Límites de interpretación | Qué no puede concluirse con estos datos | Consecuencia de 1–3 | Deben aparecer en el README y en las conclusiones |

---

## 1. Contexto operativo proporcionado (real, anonimizado)

| Área | Contexto |
|---|---|
| Negocio | Admisiones B2C de certificados online para perfiles sanitarios y no sanitarios |
| Captación | Marca nueva: redes sociales y webinars. Otros canales (web/direct, orgánico, referidos, eventos, partners) son plausibles en marcas más establecidas |
| Equipo | 5–6 asesores de ciclo completo y 1 Team Lead de apoyo (conocimiento del programa y coordinación académica) |
| Asignación | Automática según disponibilidad de agenda |
| Volumen orientativo | 100–120 leads/mes por asesor y 600–800 por equipo; más de 150 por asesor se consideraba excesivo. Son rangos de contexto, no cuotas |
| Etapas | New Lead → Opportunity → Interview Booked → Interview Held → Application Form Completed → Enrollment Link Sent → Enrolled / Closed Won; Closed Lost |
| Ruta bot | Si el bot agendaba al entrar, el lead pasaba de New Lead a Interview Booked |
| Ruta manual | Si el bot no agendaba, el lead pasaba a Opportunity para seguimiento del asesor |
| No-show | No cambiaba la etapa: el lead permanecía en Interview Booked |
| Hito central | La entrevista de admisión; todos los leads elegibles deben avanzar hacia ella |
| Motivos de pérdida | ILOC, razones financieras, preocupación por titulación oficial, convocatoria futura |
| ILOC | BD0 llamada (+ WhatsApp y email 1 si no contesta); BD1 sin acción; BD2 llamada; BD3 email 2; BD4 llamada (+ WhatsApp); BD5 email 3; BD6 cierre como ILOC. Se detiene si el candidato responde o agenda |
| Tras no-show | El bot intenta reagendar; ILOC puede activarse un par de días después |
| Recordatorios | Confirmación WhatsApp del bot, recordatorios automáticos (email/bot) y, más adelante, WhatsApp personalizado del asesor |
| Postentrevista | Email con propuesta, catálogo y enlace; el bot pide el formulario a las 24 h y 48 h; seguimiento manual del formulario |
| Cierre | Enlace de inscripción y pago; email de confirmación tras el pago |
| Gobernanza | Contacto el mismo día (máx. 24 h); reasignación si no hay contacto en 24 h; aviso si no hay seguimiento 24–48 h tras la entrevista; no cerrar sin motivo; no dejar oportunidades sin próxima tarea; no cambiar de etapa sin registro |
| Precios de referencia | Ticket habitual de 2.000–2.500 €; precio de lista de 3.200 €; descuento de campaña de 600, 500 o 350 €; 15 % adicional en pago único tras el descuento de campaña |
| Problemas observados | Respuesta tardía, baja contactabilidad, etapas sin actualizar, no-shows, seguimiento postentrevista inconsistente, emails de nurture que faltaban, oportunidades sin próxima tarea, leads estancados (especialmente en septiembre) |

---

## 2. Decisiones analíticas confirmadas

| Tema | Decisión |
|---|---|
| Dimensiones | `pipeline_stage`, `interview_outcome`, `lead_status` y `lost_reason` son independientes; el no-show solo se registra en `interview_outcome` |
| Unidad | Un `lead_id` sintético por lead-deal y un `person_key` sintético para todos los leads, usado para detectar duplicados y enlazar reactivaciones (§2.4) |
| Lead elegible | `is_duplicate = false` y `is_reactivation = false`. Los reactivados se analizan aparte |
| KPI principal | **Entrevistas realizadas / oportunidades** = leads elegibles maduros con al menos una cita `held` / **todos los leads elegibles maduros de la cohorte (ambas rutas)**. Es una métrica por lead; no se usa solo la etapa Opportunity (§2.6) |
| Métricas separadas | Conversión a entrevista realizada (todos los leads, y desglose por ruta), conversión a entrevista realizada en la ruta manual, show rate de citas concertadas |
| Show rate por cita | Citas `held` / citas `held` + `no_show`. Es una métrica por cita, con las exclusiones de §2.3 y §2.6 |
| Cohortes | Conversiones por mes de `created_at`; actividad, cierres y carga por periodo |
| Maduración | Regla por lead: maduro si `snapshot_date − created_at ≥ 60 días` (supuesto analítico). Las conversiones de cohorte usan solo leads maduros (§2.5) |
| SLA | Ruta manual: primer intento humano. Ruta bot: confirmación y contacto preentrevista, analizados aparte. Definición analítica del proyecto, no KPI histórico oficial |
| Primera respuesta | En horas naturales (decisión documentada de v1) |
| Calendario ILOC | Días hábiles lunes–viernes, sin festivos en v1; BDn es el n-ésimo día hábil desde BD0 (§2.2) |
| Duración ILOC | Depende del día en que empieza BD0; se reporta en días hábiles y en días naturales (§2.2) |
| ILOC tras no-show | Se activa tras 2 días hábiles sin respuesta |
| Entrevistas sin cita previa | No incluidas en v1 |
| Precio (regla sintética) | Pago único: (3.200 − descuento de campaña) × 0,85. Fraccionado: 3.200 − descuento de campaña. No es una reconstrucción de ventas reales |
| Finanzas | Precio de lista, descuento de campaña, descuento de pago único y `net_price` separados. Sin pagos, cobros, CAC ni ROI |
| Atribución | Cada actividad se atribuye a quien la realizó. Los cinco asesores comparten parámetros base; la conversión por asesor (por primer y por último owner) es solo exploratoria |
| Reactivación | Nuevo lead-deal con el mismo `person_key` y `is_reactivation = true`. Es una convención técnica, no una afirmación sobre el CRM real |
| Intervenciones | Efecto cero para WhatsApp personalizado, formación y reasignación |
| Equipo simulado | 5 asesores (ADV_01–ADV_05) y 1 Team Lead sin cartera, sin altas ni bajas |
| Periodo | 12 meses sintéticos con semilla fija; no reproducen fechas históricas |

### 2.1 Estados: valores permitidos y reglas de consistencia

| Dimensión | Nivel | Valores permitidos |
|---|---|---|
| `pipeline_stage` | lead (etapa actual) | `new_lead` (New Lead) · `opportunity` (Opportunity) · `interview_booked` (Interview Booked) · `interview_held` (Interview Held) · `form_completed` (Application Form Completed) · `enrollment_link_sent` (Enrollment Link Sent) · `closed_won` (Enrolled / Closed Won) · `closed_lost` (Closed Lost) |
| `interview_outcome` | cita (`activities`, filas `interview`) | `pending` · `held` · `no_show` · `rescheduled` · `cancelled` |
| `last_interview_outcome` | lead | `pending` · `held` · `no_show` · `cancelled` · nulo si no hay citas (nunca `rescheduled`) |
| `lead_status` | lead | `new` · `working` · `iloc_sequence` · `nurture` · `closed_won` · `closed_lost` |
| `lost_reason` | lead | `iloc` · `financial` · `official_qualification` · `future_intake` · nulo |

Significado de `lead_status`:
- `new`: abierto, ruta manual, sin intento humano todavía.
- `working`: abierto y en gestión (incluye leads de ruta bot con cita).
- `iloc_sequence`: abierto con la secuencia ILOC activa.
- `nurture`: deal cerrado como perdido por `future_intake` que está en la secuencia de nurture.
- `closed_won`: matriculado.
- `closed_lost`: cerrado como perdido, sin nurture activo.

| # | Regla |
|---|---|
| R1 | `pipeline_stage = closed_won` ⇔ `lead_status = closed_won` ⇔ `enrolled_at` no nulo. En ese caso `lost_reason` es nulo y los campos de precio están informados |
| R2 | `pipeline_stage = closed_lost` ⇔ `lead_status` ∈ {`closed_lost`, `nurture`} ⇔ `closed_lost_at` no nulo |
| R3 | `lost_reason` no nulo ⇒ `pipeline_stage = closed_lost`. Regla normal: `closed_lost` ⇒ `lost_reason` no nulo. **Excepción deliberada:** un `closed_lost` con `lost_reason` nulo es una anomalía inyectada (§3.8). Solo puede darse con `lead_status = closed_lost`, nunca en `nurture` ni en cierres por ILOC (R6) |
| R4 | `lead_status = nurture` ⇒ `pipeline_stage = closed_lost` y `lost_reason = future_intake` |
| R5 | `lead_status = iloc_sequence` ⇒ `pipeline_stage` ∈ {`opportunity`, `interview_booked`}, `iloc_started_at` no nulo e `iloc_ended_at` nulo |
| R6 | `lost_reason = iloc` ⇒ `iloc_end_reason = closed_iloc` y `closed_lost_at` en el día BD6 de la secuencia |
| R7 | `lead_status = new` ⇒ ruta manual, `pipeline_stage` ∈ {`new_lead`, `opportunity`} y `first_human_attempt_at` nulo |
| R8 | Ruta bot ⇒ `entered_opportunity_at` nulo. Ruta manual ⇒ `entered_opportunity_at` no nulo |
| R9 | Los timestamps de etapa no decrecen en el orden del funnel; `pipeline_stage` corresponde a la última etapa alcanzada; `closed_won` y `closed_lost` son terminales |
| R10 | Un no-show no cambia la etapa: si la última cita es `no_show` y el lead sigue abierto, `pipeline_stage = interview_booked` |
| R11 | `last_interview_outcome` es el resultado de la última cita no reemplazada; solo puede ser `pending` si esa cita tiene `interview_scheduled_for` > `snapshot_date` (§2.3). Existe al menos una cita `held` ⇔ `entered_interview_held_at` no nulo |
| R12 | `payment_type`, `list_price`, `campaign_discount`, `one_time_discount` y `net_price` solo se informan si `pipeline_stage = closed_won` |
| R13 | A las filas con `is_duplicate = true` solo se les aplican las reglas de identidad (§2.4). Se excluyen de R5–R11, de los KPIs y de los indicadores de gobernanza |

**Deal perdido por `future_intake` que entra en nurture.** Se representa con tres dimensiones sin mezclarlas: `pipeline_stage = closed_lost` (el deal está cerrado), `lost_reason = future_intake` (por qué se perdió) y `lead_status = nurture` (qué se hace operativamente con él). Las actividades de nurture se registran en ese mismo `lead_id`.
- Si la persona se reactiva, el deal original pasa a `lead_status = closed_lost` (sale de nurture y conserva `lost_reason`) y se crea un nuevo `lead_id` con el mismo `person_key` e `is_reactivation = true`. Una persona nunca tiene a la vez un deal en nurture y otro abierto.
- Si la ventana de nurture termina sin reactivación, el deal pasa a `lead_status = closed_lost`.
- `new_lead` es una etapa transitoria: el lead pasa a `opportunity` o a `interview_booked` en cuanto el bot intenta agendar.

### 2.2 Calendario de la secuencia ILOC

BDn es el n-ésimo día hábil de la secuencia contando desde BD0: se cuentan días hábiles (lunes–viernes, sin festivos en v1), nunca días naturales.
- BD1 es el día hábil inmediatamente posterior a BD0, nunca un fin de semana. Si BD0 es viernes, BD1 es el lunes siguiente.
- Los sábados y domingos no son días de la secuencia y no generan actividad.
- Solo se crea una actividad cuando el paso tiene una acción programada: BD0, BD2, BD3, BD4 y BD5. BD1 es un día hábil sin acción programada. BD6, el sexto día hábil posterior a BD0, es el día del cierre por ILOC.
- Ruta manual: BD0 es el día del primer intento de llamada. Si el lead entra en sábado o domingo, BD0 es el lunes siguiente.
- Tras un no-show: BD0 es el segundo día hábil después del día del no-show.

**Convención de conteo.** "Días transcurridos" es la diferencia entre fechas (fecha final − fecha inicial). "Fechas incluidas" cuenta ambos extremos (días transcurridos + 1). Los informes usan días transcurridos salvo que se indique lo contrario.

| BD0 | BD5 (última acción) | BD6 (cierre ILOC) | BD0→BD5: transcurridos / incluidas | BD0→BD6: transcurridos / incluidas |
|---|---|---|---|---|
| lunes | lunes siguiente | martes siguiente | 7 / 8 | 8 / 9 |
| martes | martes siguiente | miércoles siguiente | 7 / 8 | 8 / 9 |
| miércoles | miércoles siguiente | jueves siguiente | 7 / 8 | 8 / 9 |
| jueves | jueves siguiente | viernes siguiente | 7 / 8 | 8 / 9 |
| viernes | viernes siguiente | lunes de la semana posterior | 7 / 8 | 10 / 11 |

- Sin festivos, la ventana de acciones BD0–BD5 abarca siempre 8 fechas incluidas (7 días transcurridos). Es la lectura coherente con el contexto operativo ("hasta 8 días calendario").
- El cierre en BD6 cae 8 días transcurridos después de BD0 (9 fechas incluidas), o 10 días transcurridos (11 fechas incluidas) si BD0 es viernes.
- Si el lead entra en fin de semana y el primer intento es el lunes, se suma el tiempo hasta BD0: 2 días transcurridos desde sábado y 1 desde domingo. De la entrada a BD6 hay 10 días transcurridos si entra en sábado y 9 si entra en domingo.
- La duración de la secuencia se reporta en días hábiles y en días transcurridos.

### 2.3 Citas y reprogramaciones

Cada cita es una fila de `activities` con `activity_type = interview`. `activity_at` es el momento de la reserva e `interview_scheduled_for` el momento de la cita.

| `interview_outcome` | ¿Resultado terminal? | Tratamiento |
|---|---|---|
| `held` | Sí | Cuenta en el show rate |
| `no_show` | Sí | Cuenta en el show rate. El lead sigue en `interview_booked` |
| `cancelled` | Sí | Se excluye del show rate y se reporta aparte (tasa de cancelación) |
| `rescheduled` | **No.** Genera siempre una cita de reemplazo | La cita reemplazada no entra en ningún denominador del show rate. Guarda `replaced_by_activity_id`; la cita de reemplazo guarda `rescheduled_from_activity_id` |
| `pending` | No. Es una cita futura | Solo válido si `interview_scheduled_for` > `snapshot_date`. Se excluye del show rate |

- **Reprogramación:** la cita se mueve antes de celebrarse y siempre se crea la cita de reemplazo, que puede quedar `pending` si su fecha es posterior al corte. Original y reemplazo forman una cadena, y solo la última cita de la cadena puede tener resultado terminal.
- **Nueva reserva tras no-show o cancelación:** no es un reemplazo. La cita `no_show` o `cancelled` conserva su resultado terminal y la nueva cita guarda `rebooked_after_activity_id`.
- **Fecha de corte:**
  - Toda cita con `interview_scheduled_for` ≤ `snapshot_date` recibe un resultado terminal o `rescheduled`.
  - Las citas con fecha posterior al corte quedan `pending`, porque no se registra ningún hecho posterior al corte.
  - Una cita pasada con `pending` (cita vencida sin resultado) no se genera en v1. Si aparece, es un error de lógica del generador y la prueba falla.
- **Show rate por cita** = citas `held` / citas (`held` + `no_show`), solo citas con `replaced_by_activity_id` nulo e `interview_scheduled_for` ≤ `snapshot_date`.
- **Tasa de cancelación** = citas `cancelled` / citas no reemplazadas con resultado terminal (`held`, `no_show`, `cancelled`).
- **Show rate por lead** = leads con ≥1 cita `held` / leads con ≥1 cita no reemplazada con resultado `held` o `no_show`.
- Campos de `activities` que enlazan citas: `replaced_by_activity_id`, `rescheduled_from_activity_id` y `rebooked_after_activity_id`.

### 2.4 Identidad: `person_key`, duplicados y reactivaciones

- Todos los leads tienen un `person_key` sintético (`P000001`, …). Sustituye a cualquier dato personal: no se generan nombres, emails ni teléfonos.
- **Lead original:** primera fila de una persona, con `is_duplicate = false` e `is_reactivation = false`.
- **Duplicado:** segunda entrada de la misma persona, creada 0–14 días después de una fila anterior suya no duplicada, que no procede de nurture. Mismo programa, fuente igual o distinta. Lleva `is_duplicate = true`, etapa `new_lead`, `lead_status = new` y ninguna actividad.
- **Reactivación:** fila con el mismo `person_key` que un deal anterior cerrado por `future_intake` en nurture, creada 30–150 días después. Lleva `is_reactivation = true` e `is_duplicate = false`.
- **Regla de detección**, reproducible desde los datos: ordenando por `person_key` y `created_at`, una fila es duplicado si no es una reactivación y existe una fila anterior de la misma persona con `is_duplicate = false` creada ≤ 14 días antes. Las pruebas comprueban que el flag `is_duplicate` coincide exactamente con esta regla.
- Fuera de duplicados y reactivaciones, el generador no crea más de una fila por persona.
- Las reactivaciones no cuentan como leads nuevos: los KPIs de cohorte usan solo leads elegibles y los reactivados se reportan aparte.

### 2.5 Madurez de leads y cohortes

- **Lead maduro:** `snapshot_date − created_at ≥ 60 días`, calculado con timestamps completos (60 × 24 h).
- **Cohorte mensual** (por mes de `created_at`):
  - `madura`: el 100 % de sus leads elegibles son maduros.
  - `parcial`: solo una parte de sus leads elegibles es madura.
  - `inmadura`: ningún lead elegible es maduro.
- Las conversiones de cohorte se calculan solo con leads maduros. En una cohorte parcial se indica qué fracción entra en el cálculo, y esa cohorte no se compara con las maduras. Un mes no se etiqueta como maduro solo porque parte de sus leads haya alcanzado los 60 días.
- Con la fecha de corte propuesta (2025-12-31 23:59), la regla equivale a un umbral de creación de 2025-11-01 23:59 (corte − 60 × 24 h).
- La etiqueta de cada cohorte no se declara de antemano: se calcula con la proporción de leads elegibles maduros de esa cohorte. El notebook muestra, para cada mes, los leads elegibles, los maduros, la proporción y la etiqueta resultante.
- Los indicadores de periodo (actividad, carga, gobernanza) no dependen de la madurez.

### 2.6 Métricas de entrevista: unidad de conteo

Las métricas por lead cuentan leads y las métricas por cita cuentan citas. Nunca se usan resultados de citas como si fueran conteos de leads.

| Métrica | Unidad | Numerador | Denominador | Base temporal |
|---|---|---|---|---|
| **KPI principal: entrevistas realizadas / oportunidades** | lead | leads elegibles maduros con al menos una cita `held` | todos los leads elegibles maduros de ambas rutas | cohorte por `created_at` |
| Conversión a entrevista realizada por ruta | lead | lo mismo, filtrado por `entry_path` | leads elegibles maduros de esa ruta | cohorte |
| **Show rate por cita** | cita | citas `held` | citas `held` + `no_show` | mes de `interview_scheduled_for` |
| Show rate por lead | lead | leads con al menos una cita `held` | leads con al menos una cita elegible con resultado `held` o `no_show` | cohorte |
| Tasa de cancelación | cita | citas `cancelled` | citas elegibles con resultado `held`, `no_show` o `cancelled` | mes de `interview_scheduled_for` |

**Cita elegible:** cita de un lead elegible (sin duplicados), con `replaced_by_activity_id` nulo (no reemplazada por reprogramación) e `interview_scheduled_for` ≤ `snapshot_date`. Por tanto, quedan fuera las citas `rescheduled` y las `pending`; las `cancelled` solo entran en la tasa de cancelación.

---

## 3. Parámetros del escenario sintético (pendientes de aprobación)

Todos los valores de esta sección son **parámetros del escenario sintético**: arbitrarios, elegidos para que el escenario sea analizable. No son tasas realistas, calibradas ni esperadas. Se guardan en `config/simulation_params.yaml` y se generan con semilla 42.

### 3.1 Periodo, semilla y volumen

| Parámetro | Valor propuesto | Nota |
|---|---|---|
| Calendario | 2025-01-01 a 2025-12-31 | Se usa un año de calendario solo para tener días de la semana reales; no corresponde a ningún periodo histórico |
| Fecha de corte (`snapshot_date`) | 2025-12-31 23:59 | Deja pipeline abierto y cohortes de noviembre y diciembre inmaduras, para poder medir gobernanza |
| Semilla | 42 | |
| Volumen mensual del escenario: leads elegibles nuevos (equipo) | Ene 640 · Feb 620 · Mar 620 · Abr 600 · May 620 · Jun 600 · Jul 600 · Ago 600 · **Sep 780** · Oct 680 · Nov 640 · Dic 600 | Ruido Poisson y recorte a [600, 800]. Los duplicados (§3.8) y las reactivaciones (§3.7) se generan aparte y no cuentan en este volumen |
| Distribución por día de la semana | Lun–Vie peso 1,0 · Sáb 0,5 · Dom 0,6 | |
| Hora de entrada | Picos 10–14 h y 18–22 h; ~15 % entre 22–08 h | Relevante para el SLA en horas naturales |
| Peso de asignación por asesor | ADV_01 0,23 · ADV_02 0,21 · ADV_03 0,20 · ADV_04 0,19 · ADV_05 0,17 | Parámetro de asignación del escenario. No representa una distribución real ni dice nada del desempeño individual |
| Horario de trabajo de asesores | Lun–Vie 09:00–19:00 | El bot opera 24/7 |

**Comprobación de carga esperada por asesor y mes**

- **Definición de carga:** leads elegibles (sin duplicados ni reactivaciones) asignados por `first_owner_id` y mes de `created_at`. Los reactivados se reportan en una columna aparte. Las reasignaciones no cambian la carga, porque se mide por primer owner.
- **Fórmula:** carga esperada = volumen mensual del escenario × peso de asignación del asesor. Son valores esperados antes del azar. El notebook mostrará la carga realizada.

| Volumen del escenario | Meses | ADV_01 (0,23) | ADV_02 (0,21) | ADV_03 (0,20) | ADV_04 (0,19) | ADV_05 (0,17) | Suma |
|---|---|---|---|---|---|---|---|
| 600 | abr, jun, jul, ago, dic | 138,0 | 126,0 | 120,0 | 114,0 | 102,0 | 600 |
| 620 | feb, mar, may | 142,6 | 130,2 | 124,0 | 117,8 | 105,4 | 620 |
| 640 | ene, nov | 147,2 | 134,4 | 128,0 | 121,6 | 108,8 | 640 |
| 680 | oct | **156,4** | 142,8 | 136,0 | 129,2 | 115,6 | 680 |
| 780 | sep | **179,4** | **163,8** | **156,0** | 148,2 | 132,6 | 780 |

- Hay valores esperados por encima de 150 en octubre (ADV_01) y en septiembre (ADV_01–03). No dependen solo del pico de septiembre: el peso de asignación desigual también los produce.
- ADV_01 tiene valores esperados de 138,0–147,2 el resto del año. Con la variación aleatoria (desviación típica del orden de √carga, unos 12 leads por asesor y mes), la carga realizada puede superar 150 también en esos meses.
- La mayoría de los valores esperados supera 120. Es consecuencia de combinar 5 asesores con 600–800 leads de equipo; no es un hallazgo ni un indicador de desempeño.
- Alternativa: con pesos iguales (0,20), la carga esperada es 120,0–128,0 la mayoría de meses, 136,0 en octubre y 156,0 para todos en septiembre.

### 3.2 Fuentes, rutas, perfiles y programas

| `channel_group` | Peso | % ruta bot | Modificador de conversión |
|---|---|---|---|
| paid_social | 45 % | 25 % | 0,85 |
| webinar | 25 % | 40 % | 1,15 |
| web_direct | 12 % | 35 % | 1,05 |
| organic | 8 % | 30 % | 1,00 |
| referral | 5 % | 30 % | 1,25 |
| event | 3 % | 20 % | 1,00 |
| partner | 2 % | 20 % | 1,10 |

- La proporción total de la ruta bot queda en torno al 30 %, como resultado de los pesos de la tabla.
- El modificador de conversión es multiplicativo sobre: contacto, reserva tras contacto, formulario y matrícula. Las probabilidades se limitan a un máximo de 0,95.

| Parámetro | Valor propuesto |
|---|---|
| `candidate_profile` | sanitario 55 % · no_sanitario 45 % |
| Programas | PRG_A, PRG_B (orientados a sanitario) y PRG_C, PRG_D (orientados a no sanitario); todos con lista de 3.200 € |
| Programa si el perfil es sanitario | A 55 % · B 35 % · C 5 % · D 5 % |
| Programa si el perfil es no sanitario | C 50 % · D 40 % · A 5 % · B 5 % |
| Modificador por perfil (formulario) | sanitario 1,05 · no_sanitario 0,95 |

### 3.3 Contacto, SLA e ILOC (ruta manual)

| Parámetro | Valor propuesto |
|---|---|
| Mediana del retraso del primer intento, dentro de horario (h) | 3 h para los cinco asesores (lognormal, σ = 1,0) |
| Lead fuera de horario | El primer intento se calcula desde la siguiente apertura de horario |
| Leads manuales nunca tocados | 2 % (anomalía) |
| Reasignación por SLA | Si no hay intento en 24 h naturales: reasignación con prob. 0,80; nuevo intento en ≤ 2 h hábiles. Efecto cero sobre la conversión posterior |
| Prob. de contacto por paso | BD0 llamada 0,35 · respuesta a WhatsApp/email 1: 0,08 · BD2 llamada 0,22 · BD3 email 0,04 · BD4 llamada 0,22 · WhatsApp 0,06 · BD5 email 0,04 |
| ILOC tras no-show | Mismas probabilidades × 0,7 |
| Reserva tras contacto (ruta manual) | 0,55 |
| Contactado sin reserva, motivo de cierre | financial 35 % · official_qualification 35 % · future_intake 30 % |

### 3.4 Entrevistas

| Parámetro | Ruta manual | Ruta bot |
|---|---|---|
| Programación | 1–5 días hábiles tras el contacto, entre 09–19 h | 1–4 días hábiles tras la entrada |
| Resultado por cita: held | 0,65 | 0,55 |
| no_show | 0,22 | 0,30 |
| rescheduled (reemplazo, no final) | 0,08 | 0,09 |
| cancelled | 0,05 | 0,06 |

| Regla | Valor propuesto |
|---|---|
| Máximo de citas por lead | 3, contando reemplazos y nuevas reservas. Si se alcanza el tope, el resultado de la última cita se sortea solo entre held, no_show y cancelled (probabilidades renormalizadas) |
| Tras no-show | Nueva reserva (`rebooked_after_activity_id`) en ≤ 2 días hábiles con prob. 0,40; si no, ILOC con BD0 = segundo día hábil tras el no-show. Si responde durante ILOC: nueva reserva con prob. 0,70 |
| Tras rescheduled | Cita de reemplazo programada 1–5 días hábiles después, enlazada con `rescheduled_from_activity_id` / `replaced_by_activity_id` |
| Tras cancelled | Nueva reserva (`rebooked_after_activity_id`) con prob. 0,30; si no, cierre con la misma mezcla que "contactado sin reserva" |
| Confirmación WhatsApp del bot (ruta bot) | Enviada en el 95 % de los casos |
| Recordatorio automático 24 h antes | Enviado en el 97 % de las citas |
| WhatsApp personalizado del asesor | 0 % hasta el 30 de junio; 60 % de las citas desde el 1 de julio. **Efecto cero** sobre el show |
| Contacto humano preentrevista (ruta bot) | 35 % |

### 3.5 Postentrevista y cierre

| Transición | Probabilidad base | Tiempo |
|---|---|---|
| Entrevista realizada → formulario | 0,45 | lognormal, mediana 2 días, máx. 14 |
| Formulario → enlace enviado | 0,85 | mediana 2 días, máx. 10 |
| Enlace → matrícula | 0,65 | mediana 4 días, máx. 21 |
| Cierre sin formulario | — | 7–21 días tras la entrevista |
| Cierre tras enlace sin matrícula | — | 10–30 días tras el enlace |

| Regla | Valor propuesto |
|---|---|
| Recordatorios de formulario del bot | A las 24 h y 48 h, si el formulario no se ha recibido aún |
| Email postentrevista enviado en ≤ 24 h | 85 % |
| Seguimiento del asesor en ≤ 48 h tras la entrevista | 80 % |
| `next_step_agreed = true` | 70 %. **Efecto cero** sobre la conversión |
| Motivo de pérdida: entrevista sin formulario | financial 40 % · official_qualification 25 % · future_intake 35 % |
| Motivo de pérdida: formulario sin enlace | financial 50 % · future_intake 50 % (no se modela rechazo académico) |
| Motivo de pérdida: enlace sin matrícula | financial 60 % · future_intake 40 % |

No hay modificador por asesor: los cinco asesores comparten los mismos parámetros base (1,00) en respuesta y conversión.

**Campos postentrevista** (valores permitidos):
- `candidate_situation`: employed / unemployed / student / career_change
- `immediate_interest` y `program_interest`: high / medium / low
- `decision_maker`: self / shared / other
- `main_objection`: price / time / official_qualification / timing / none
- `payment_preference`: single / installments / undecided

Coherencia entre campos: si el lead se pierde por `financial`, `main_objection = price` con prob. 0,70; si se pierde por `official_qualification`, `main_objection = official_qualification` con prob. 0,70.

### 3.6 Precios (regla sintética)

| Parámetro | Valor propuesto |
|---|---|
| Descuento de campaña | Sorteo aleatorio en cada matrícula, independiente de la fecha: 600 € 30 % · 500 € 40 % · 350 € 30 %. Escenario sintético arbitrario |
| Mezcla de modalidad | single 55 % · installments 45 %; si `main_objection = price`: installments 65 % |

| Descuento campaña | Neto pago único | Descuento pago único | Neto fraccionado |
|---|---|---|---|
| 600 € | 2.210,00 € | 390,00 € | 2.600,00 € |
| 500 € | 2.295,00 € | 405,00 € | 2.700,00 € |
| 350 € | 2.422,50 € | 427,50 € | 2.850,00 € |

Los netos de pago fraccionado quedan por encima del rango de ticket observado (2.000–2.500 €). No se corrige artificialmente; se documenta como límite de la regla sintética.

### 3.7 Nurture y reactivación

| Parámetro | Valor propuesto |
|---|---|
| `future_intake` que entra en nurture | 85 % (`lead_status = nurture`) |
| Emails de nurture | 3, cada ~30 días |
| Emails no enviados o fallidos | 15 % |
| Reactivación | 12 % de las personas en nurture, entre 30 y 150 días después; crea un nuevo lead-deal con `is_reactivation = true` y el mismo `person_key` |
| Conversión del reactivado | Mismos parámetros que un lead manual (sin efecto adicional) |

### 3.8 Leads estancados y anomalías de calidad

| Anomalía | Tasa propuesta |
|---|---|
| Duplicados (regla de §2.4) | 2 % adicional sobre los leads elegibles nuevos, creados 0–14 días después del original |
| Cerrados perdidos sin `lost_reason` | 3 % de los perdidos |
| Leads abiertos sin tarea abierta | 8 % de los abiertos |
| Leads abiertos con tarea vencida | 15 % de los abiertos |
| Cambio de etapa sin actividad de soporte (±24 h) | 4 % de las transiciones |
| Entrevistados con ≥1 campo postentrevista vacío | 10 % |
| Estancamiento (sin actividad posterior, lead abierto) | Opportunity contactada 4 % · Interview Held 5 % · Form Completed 3 %; × 2 en septiembre |

**Anomalías deliberadas frente a errores de lógica.** Cada anomalía es una excepción deliberada a una regla normal y tiene un ámbito permitido. Las pruebas detectan y reportan cada anomalía (recuento y tasa). Una violación fuera del ámbito permitido indica un error de lógica del generador y hace fallar la prueba. Si la tasa observada se aleja del parámetro, se emite un aviso, no un fallo.

| Anomalía deliberada | Regla normal que exceptúa | Ámbito permitido | Error de lógica (la prueba falla) |
|---|---|---|---|
| Cierre sin `lost_reason` | `closed_lost` ⇒ `lost_reason` no nulo (R3) | `pipeline_stage = closed_lost` y `lead_status = closed_lost`, cierre no producido por ILOC | `lost_reason` nulo en nurture, en un cierre ILOC, en un lead abierto o ganado |
| Lead manual nunca tocado | Primer intento humano en la ruta manual | Ruta manual, lead abierto con `lead_status = new` | Lead cerrado sin ninguna actividad |
| Abierto sin tarea abierta | Toda oportunidad abierta tiene próxima tarea | Leads abiertos | `has_open_task` incoherente con las tareas de `activities` |
| Tarea vencida | Tareas completadas a tiempo | Leads abiertos | Tarea vencida abierta en un lead cerrado |
| Cambio de etapa sin actividad de soporte | Toda transición tiene actividad en ±24 h | Cualquier timestamp de etapa | Timestamps de etapa fuera de orden (R9) |
| Campos postentrevista vacíos | Campos completos desde Interview Held | Leads con entrevista realizada | Campos postentrevista informados en un lead sin entrevista realizada |
| Lead estancado | Actividad continuada en leads abiertos | Leads abiertos en Opportunity contactada, Interview Held o Form Completed | Lead cerrado marcado como estancado |
| Duplicado | Una fila por persona y deal | Filas que cumplen la regla de §2.4 | `is_duplicate` no coincide con la regla de detección |

### 3.9 Notas de implementación (generador v1)

Decisiones tomadas al implementar la §3 que el texto aprobado no especificaba. No cambian ningún valor aprobado.

| Tema | Implementación |
|---|---|
| Método de simulación | Se simula el ciclo de vida completo de cada lead y después se corta en `snapshot_date`: no se registra nada posterior al corte y los estados se derivan de los eventos hasta ese momento |
| Últimas entradas | No se crea ningún lead en los 30 minutos previos al corte, para que el enrutamiento (bot / Opportunity) ocurra siempre antes del corte |
| Retraso del primer intento | Lognormal en **horas de trabajo** (lunes–viernes 09–19) desde la siguiente apertura; el SLA se mide en horas naturales (§2) |
| Reasignación | Se comprueba en el primer momento laborable tras 24 horas naturales; el nuevo owner intenta el contacto en ≤ 2 horas de trabajo |
| Seguimiento del asesor tras la entrevista | El parámetro del 80 % es la proporción *planificada* dentro de 48 horas naturales; la actividad del asesor se desplaza después a horario laboral, así que la proporción realizada en 48 h es menor |
| Registros de soporte de etapa | Cada cambio de etapa tiene un registro dedicado en el mismo momento (intento de reserva del bot, reserva, hora de la cita, formulario recibido, enlace de matrícula, pago confirmado, nota de cierre). La omisión del 4 % (§3.8) se aplica a los omitibles: opportunity, form_completed y closed_lost |
| Tareas vencidas | El 15 % se aplica a la tarea de seguimiento creada para leads abiertos sin tarea de secuencia pendiente; los leads estancados siempre tienen una tarea vencida |
| Reactivaciones | Un lead reactivado puede volver a entrar en nurture, pero en v1 no se reactiva una segunda vez |
| ILOC y contacto | La llamada de BD0 se etiqueta `first_contact` (o `reschedule` tras un no-show) si conecta, e `iloc` si no conecta y se inicia la secuencia |
| Verdad de referencia | Las anomalías inyectadas se listan en `data/dq_ground_truth.csv`, una ayuda de validación que usan las pruebas; no es una tabla analítica |

---

## 4. Límites de interpretación

| Límite | Implicación |
|---|---|
| Datos 100 % sintéticos | Ningún resultado describe a la empresa, al equipo ni al mercado reales |
| Los resultados reflejan los parámetros | Las diferencias entre fuentes, rutas y perfiles reproducen los parámetros del escenario sintético (§3); el proyecto demuestra método, no descubre hechos |
| Sin causalidad | Efecto cero programado para WhatsApp, formación, reasignación y siguiente paso agendado. Cualquier diferencia observada es ruido o mezcla. Para estimar efectos haría falta un piloto controlado |
| Carga y asesores | El peso de asignación desigual es un parámetro del escenario, no una distribución real. Los cinco asesores comparten parámetros base, así que cualquier diferencia de carga o conversión procede del azar, del peso de asignación y de las reasignaciones, y no se atribuye a desempeño individual. Solo exploratoria |
| Precio | La regla sintética no reconstruye el ticket histórico; los netos fraccionados quedan fuera del rango observado |
| Descuento | Asignación aleatoria sin patrón temporal; no permite analizar estacionalidad de campañas |
| Sin admisión académica | No se modela quién aprueba ni rechazos por elegibilidad |
| Sin convocatorias ni plazas | No se puede estimar ocupación de grupos |
| Sin pagos ni gasto | No hay cobro, impago, CAC ni ROI |
| Calendario simplificado | Sin festivos; primera respuesta en horas naturales; horario de asesores supuesto |
| Reactivación | Convención técnica (nuevo lead-deal); no describe el comportamiento real del CRM |
| Madurez | Solo los leads con `snapshot_date − created_at ≥ 60 días` entran en las conversiones de cohorte; las cohortes parciales e inmaduras no se comparan con las maduras (§2.5) |
