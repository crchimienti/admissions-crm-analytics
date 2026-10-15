**Language:** English | [Español](kpi_definitions.es.md)

# KPI definitions (v1)

> These are **project analytical definitions**, not official historical KPIs. All values computed from them in this repository are synthetic.

## 0. Conventions

| Term | Definition |
|---|---|
| Eligible lead | `is_duplicate = false` and `is_reactivation = false`. Reactivations are reported separately |
| Mature lead | `snapshot_date − created_at ≥ 60 days` (full timestamps) |
| Cohort | month of `created_at`. Label computed from the share of mature eligible leads: `mature` (100 %), `partial` (some), `immature` (none). Cohort conversions use mature leads only; partial cohorts show the share included and are not compared with mature ones |
| Period | month of the event timestamp (activity, appointment slot, enrollment); used for activity, workload, show rate and governance |
| Eligible appointment | appointment of an eligible lead, not replaced by rescheduling (`replaced_by_activity_id` null) and with `interview_scheduled_for` ≤ `snapshot_date` |
| Open lead | `pipeline_stage` not in {`closed_won`, `closed_lost`} at the snapshot |

## 1. Main KPI and interview metrics

| KPI | Unit | Numerator | Denominator | Base |
|---|---|---|---|---|
| **Interviews held / opportunities (main KPI)** | lead | mature eligible leads with ≥ 1 `held` appointment | **all** mature eligible leads, both routes | cohort |
| Conversion to held interview, manual route | lead | the same, `entry_path = manual` | mature eligible manual leads | cohort |
| Conversion to held interview, bot route | lead | the same, `entry_path = bot_booked` | mature eligible bot-route leads | cohort |
| Booking rate | lead | mature eligible leads with `entered_interview_booked_at` | mature eligible leads | cohort |
| **Per-appointment show rate** | appointment | eligible appointments `held` | eligible appointments `held` + `no_show` | month of `interview_scheduled_for` |
| Per-lead show rate | lead | leads with ≥ 1 eligible `held` appointment | leads with ≥ 1 eligible appointment `held` or `no_show` (mature cohorts) | cohort |
| Cancellation rate | appointment | eligible appointments `cancelled` | eligible appointments `held`, `no_show` or `cancelled` | month of `interview_scheduled_for` |

"Opportunities" in the main KPI means all eligible inbound leads. The Opportunity stage alone is never used as the denominator, because it would leave out the bot route. Appointment outcomes are never used as lead counts.

## 2. Funnel (mature cohorts)

| KPI | Numerator | Denominator |
|---|---|---|
| Forms completed / interviews held | leads with `entered_form_completed_at` | leads with `entered_interview_held_at` |
| Enrollments / interviews held | leads with `enrolled_at` | leads with `entered_interview_held_at` |
| Links / forms | leads with `entered_enrollment_link_sent_at` | leads with `entered_form_completed_at` |
| Enrollments / eligible leads | leads with `enrolled_at` | mature eligible leads |
| Sales cycle | median and mean of `enrolled_at − created_at`, in days | enrolled mature leads |

## 3. Entry and SLA (project analytical definition)

| KPI | Numerator | Denominator |
|---|---|---|
| Route share | eligible leads by `entry_path` | eligible leads |
| Contacted (manual) | manual leads with `first_human_attempt_at` | eligible manual leads |
| Untouched (manual) | open manual leads without a human attempt at the snapshot | open eligible manual leads |
| First attempt ≤ 24 h (manual) | `first_human_attempt_at − created_at` ≤ 24 calendar hours | manual leads created ≥ 24 h before the snapshot (complete window) |
| First attempt same day (manual) | first attempt on the calendar date of `created_at` | same denominator |
| First response, median and p90 | `first_human_attempt_at − created_at` in calendar hours | manual leads with an attempt (same window) |
| Contact rate | leads with `first_connected_at` | leads with ≥ 1 human attempt |
| Reassignment rate | manual leads with `reassigned_flag` | eligible manual leads |
| Bot route: pre-interview confirmation | bot-route leads with a bot confirmation/reminder before the first appointment | eligible bot-route leads |
| Bot route: human pre-interview contact | bot-route leads with a manual advisor activity before the first appointment | eligible bot-route leads |

First response is measured in **calendar hours** (documented v1 decision). Calendar hours include nights and weekends, when the scenario's advisors (Mon–Fri 09–19) do not work, so this definition can penalise leads that arrive outside working hours. The notebook reports the observed SLA for weekday and weekend arrivals separately; the split describes the scenario and does not show that every weekend lead misses the target.

## 4. Sources, profiles, programmes (mature cohorts)

For each segment: leads, held / leads, enrolled / leads, enrolled / held, ILOC share (lost for `iloc` / leads), net € per lead (Σ `net_price` / leads). Differences reproduce the scenario modifiers.

## 5. Advisors (exploratory)

| Indicator | Definition |
|---|---|
| Workload | eligible leads by `first_owner_id` and `created_at` month; reactivations reported separately; duplicates excluded |
| Expected workload | scenario monthly volume × assignment weight (before randomness) |
| Bands | < 100, 100–120 usual, 121–150 high, > 150 alert |
| Conversion | held / leads and enrolled / leads by `first_owner_id` and by `current_owner_id`, with n and 95 % Wilson interval |
| Activity | activities attributed to `actor_id` (whoever performed them) |

All advisors share the same base parameters: differences are not attributed to individual performance.

## 6. Losses and nurture

| KPI | Numerator | Denominator |
|---|---|---|
| Lost-reason distribution | closed-lost leads by reason | closed-lost leads with a reason |
| Lost reasons by exit point | cross-tab of reason × last stage reached before closing | — |
| Reactivation | nurture deals ended as `reactivated` | nurture deals whose 150-day window is complete by the snapshot |
| Nurture email failure | nurture emails `not_sent` or `failed` | nurture emails scheduled |

## 7. CRM governance (at the snapshot)

| Indicator | Numerator | Denominator |
|---|---|---|
| Open without next task | open leads with `has_open_task = false` | open eligible leads |
| Open with overdue task | open leads with ≥ 1 task `overdue` | open eligible leads |
| Manual advisor follow-up within 48 h | eligible leads with ≥ 1 advisor activity that is `outbound`, a `call` or `whatsapp`, and not automated, in the window (first held interview, first held interview + 48 calendar hours]; weekends are not excluded; activities before the interview never count | eligible leads whose first held interview is ≥ 48 h before the snapshot |
| Closed-lost without reason | `closed_lost` with null `lost_reason` | closed-lost leads |
| Incomplete post-interview fields | interviewed leads with ≥ 1 null post-interview field | interviewed leads |
| Stage change without its support record | stage events with no dedicated record at the same timestamp (data-quality rule, matched with the ground truth) | omittable stage events (opportunity, form_completed, closed_lost) |
| Stage change with no activity within ± 24 h | stage events with no activity of the lead within ± 24 h (looser governance view; a subset of the previous row) | all stage events |
| Duplicates | `is_duplicate = true` | all rows |

## 8. Finance (enrolled leads, period view)

Gross list value Σ `list_price`; campaign discount Σ `campaign_discount`; one-time discount Σ `one_time_discount`; net price Σ and mean of `net_price`, overall and by `payment_type`; payment-type mix. No payments, collections, CAC or ROI in v1.
