**Language:** English | [Español](data_dictionary.es.md)

# Data dictionary (v1)

> All files are **synthetic**. Identifiers (`lead_id`, `person_key`, `ADV_0x`, `PRG_x`) are invented; no names, emails, phone numbers or real records exist in the dataset. Timestamps are local, naive (no time zone), floored to the second.

Files: `data/leads.csv` (one row per lead-deal, snapshot at `snapshot_date`), `data/activities.csv` (one row per activity), `data/dq_ground_truth.csv` (validation aid listing injected anomalies).

## 1. `leads.csv`

### 1.1 Identity and acquisition

| Column | Type | Allowed values / rule |
|---|---|---|
| `lead_id` | string | `L000001`…; unique; ordered by `created_at` |
| `person_key` | string | `P000001`…; present on every row; links duplicates and reactivations to the same synthetic person (§2.4 of assumptions) |
| `is_reactivation` | bool | true if the row comes from nurture; reported separately, never counted as a new lead |
| `reactivated_from_lead_id` | string | parent deal (closed for `future_intake`, in nurture); null otherwise |
| `is_duplicate` | bool | true if the row matches the duplicate rule: not a reactivation and an earlier non-duplicate row of the same person created ≤ 14 days before |
| `is_synthetic` | bool | always true |
| `created_at` | datetime | lead arrival |
| `source` | string | sub-source within the channel (e.g. `webinar_live`) |
| `channel_group` | string | `paid_social`, `webinar`, `web_direct`, `organic`, `referral`, `event`, `partner` |
| `program_alias` | string | `PRG_A`, `PRG_B` (healthcare-oriented), `PRG_C`, `PRG_D` (non-healthcare-oriented) |
| `candidate_profile` | string | `healthcare`, `non_healthcare` |
| `entry_path` | string | `bot_booked` (bot booked on entry) or `manual` (Opportunity, advisor follow-up); null for duplicates |

### 1.2 Ownership and contact

| Column | Type | Rule |
|---|---|---|
| `first_owner_id` | string | advisor assigned on entry (`ADV_01`…`ADV_05`) |
| `current_owner_id` | string | owner at the snapshot; differs from the first owner only after a reassignment |
| `reassigned_flag`, `reassigned_at` | bool, datetime | SLA reassignment (manual route), at or after 24 calendar hours |
| `first_human_attempt_at` | datetime | first advisor outbound call or WhatsApp that is not automated |
| `first_connected_at` | datetime | first connected call, inbound reply from the candidate, or held interview |

### 1.3 Stages and states

| Column | Type | Rule |
|---|---|---|
| `entered_opportunity_at` | datetime | manual route only (null on the bot route) |
| `entered_interview_booked_at` | datetime | first booking (`activity_at` of the first interview row) |
| `entered_interview_held_at` | datetime | first `held` appointment (its `interview_scheduled_for`) |
| `entered_form_completed_at`, `entered_enrollment_link_sent_at` | datetime | milestones |
| `enrolled_at` | datetime | closed won (payment confirmed) |
| `closed_lost_at` | datetime | closed lost |
| `pipeline_stage` | string | `new_lead`, `opportunity`, `interview_booked`, `interview_held`, `form_completed`, `enrollment_link_sent`, `closed_won`, `closed_lost` — last stage reached by the snapshot |
| `lead_status` | string | `new`, `working`, `iloc_sequence`, `nurture`, `closed_won`, `closed_lost` (meanings in assumptions §2.1) |
| `last_interview_outcome` | string | outcome of the last non-replaced appointment: `pending`, `held`, `no_show`, `cancelled`; never `rescheduled`; null if no appointment |
| `lost_reason` | string | `iloc`, `financial`, `official_qualification`, `future_intake`; null if not lost, or deliberately null on a `closed_lost` row (anomaly) |

Consistency rules R1–R13 are in assumptions §2.1 and are enforced by `tests/test_integrity.py`.

### 1.4 ILOC and nurture

| Column | Type | Rule |
|---|---|---|
| `iloc_started_at` | datetime | activation of the latest ILOC episode started by the snapshot (BD0 WhatsApp + email 1) |
| `iloc_ended_at`, `iloc_end_reason` | datetime, string | `responded`, `booked`, `closed_iloc`; null while the episode is active |
| `iloc_episode_count` | int | ILOC episodes started by the snapshot (initial and/or after a no-show) |
| `nurture_started_at` | datetime | = `closed_lost_at` for `future_intake` deals that enter nurture |
| `nurture_ended_at`, `nurture_end_reason` | datetime, string | `reactivated` (= child's `created_at`) or `window_ended` (150 days); null while in nurture |

### 1.5 Governance, post-interview fields and pricing

| Column | Type | Rule |
|---|---|---|
| `has_open_task`, `next_task_due_at` | bool, datetime | derived from tasks with status `open` or `overdue` |
| `candidate_situation` | string | `employed`, `unemployed`, `student`, `career_change` |
| `immediate_interest`, `program_interest` | string | `high`, `medium`, `low` |
| `decision_maker` | string | `self`, `shared`, `other` |
| `main_objection` | string | `price`, `time`, `official_qualification`, `timing`, `none` |
| `payment_preference` | string | `single`, `installments`, `undecided` |
| `next_step_agreed` | bool | zero programmed effect on conversion |
| `payment_type` | string | `single`, `installments` — closed won only |
| `list_price` | float | 3,200 |
| `campaign_discount` | float | 600, 500 or 350 (random draw; arbitrary scenario) |
| `one_time_discount` | float | single: (3,200 − campaign discount) × 0.15; installments: 0 |
| `net_price` | float | list − campaign discount − one-time discount |
| `snapshot_date` | datetime | 2025-12-31 23:59:00 |

The seven post-interview fields are filled only after an interview is held; about 10 % of interviewed leads have at least one empty field (anomaly).

## 2. `activities.csv`

| Column | Type | Allowed values / rule |
|---|---|---|
| `activity_id` | string | `A0000001`…; ordered by `activity_at` |
| `lead_id` | string | must exist in `leads.csv`; duplicates have no activities |
| `activity_at` | datetime | when the activity happened (for interviews: when the appointment was booked; for tasks: when the task was created) |
| `actor_type` | string | `advisor`, `bot`, `system`, `candidate` (inbound replies) |
| `actor_id` | string | advisor who performed it; null for bot, system and candidate |
| `activity_type` | string | `call`, `whatsapp`, `email`, `interview`, `task`, `note` |
| `direction` | string | `outbound`, `inbound`, `internal` (interviews, tasks, notes) |
| `is_automated` | bool | templated or bot messages (sequence emails, reminders); manual advisor calls and WhatsApps are false |
| `sequence_name` | string | `booking`, `first_contact`, `iloc`, `reschedule`, `pre_interview_reminder`, `post_interview`, `form_reminder`, `form`, `enrollment`, `nurture`, `none` |
| `sequence_step` | string | e.g. `BD0`, `BD2_call_task`, `reminder_24h`, `personal_whatsapp`, `nurture_email_2`, `closed_lost` |
| `sequence_instance` | int | ILOC episode number within the lead |
| `business_day_index` | int | ILOC only: 0, 2, 3, 4, 5 (actions), 6 (closing note); never 1 |
| `call_outcome` | string | `connected`, `no_answer`, `voicemail`, `wrong_number` |
| `email_status` | string | `sent`, `not_sent`, `failed` (failures only in nurture) |
| `interview_scheduled_for` | datetime | appointment slot |
| `interview_outcome` | string | `pending` (slot after the snapshot), `held`, `no_show`, `rescheduled` (replaced, not terminal), `cancelled` |
| `interviewer_id` | string | owner at the appointment time |
| `rescheduled_from_activity_id` / `replaced_by_activity_id` | string | reschedule chain (replacement ↔ replaced appointment) |
| `rebooked_after_activity_id` | string | new booking after a `no_show` or `cancelled` appointment (not a replacement) |
| `task_due_at`, `task_completed_at` | datetime | tasks only |
| `task_status` | string | `open`, `overdue` (due before the snapshot, not done), `done`, `cancelled` (sequence stopped) |

## 3. `dq_ground_truth.csv` (validation aid)

| Column | Meaning |
|---|---|
| `lead_id` | affected lead |
| `issue_type` | `duplicate`, `missing_lost_reason`, `untouched_manual`, `open_without_task`, `overdue_task`, `stage_support_omitted`, `empty_post_interview_fields`, `stalled` |
| `detail` | stage or fields involved; for `overdue_task`: `injected` or `stalled_lead` |

The tests compare each detection rule with this file in the same unit (lead, or lead + stage for `stage_support_omitted`). A detection outside the injected set, or an injected case that the rule can observe but does not detect, is a logic error. Injected cases the rule cannot observe yet at the snapshot (recent untouched or stalled leads) are counted separately.
