**Language:** English | [Español](canonical_schema.es.md)

# Canonical CRM schema `crm-canonical/0.1.1` (F2)

> All data in this project is **synthetic**. F2 adds a canonical, file-based representation of the admissions data and a validated path from it to the existing metric code. It does not connect to any CRM, read real data, add an application, or claim that the schema fits other funnels. Only the admissions profile exists. Portability would have to be tested in a later phase.

## 1. Why and what

Before F2, `src/metrics.py` read the two admissions CSV files directly. F2 puts a neutral contract in between:

```
data/leads.csv + data/activities.csv
   └─ src/canonical/mapping.py          (profiles/admissions/mapping_csv_v1.yaml)
        └─ canonical tables              (schema/canonical_v0.1.1.yaml, checked by src/canonical/validate.py)
             └─ src/canonical/adapters/admissions.py   (profiles/admissions/rules.yaml, kpi_requirements.yaml)
                  └─ src/metrics.py (F1 + authorised v1.2.1-f2 robustness fix)  +  src/canonical/history.py
```

The admissions adapter rebuilds exactly the frames `metrics.py` reads, so the 47 baseline metrics are identical to F0 and F1 when they are computed through the canonical route. The tests check this metric by metric.

## 2. Tables

One CSV file per table (UTF-8, header row, empty cell = null). Full column list, types and nullability: [`schema/canonical_v0.1.1.yaml`](../schema/canonical_v0.1.1.yaml), an additive revision of [`schema/canonical_v0.1.yaml`](../schema/canonical_v0.1.yaml) (kept unchanged). Datasets may declare `crm-canonical/0.1` or `crm-canonical/0.1.1`; only 0.1.1 may carry `stage_events.seq`.

| Table | Required | Key | Content |
|---|---|---|---|
| `dataset` | yes (1 row) | `dataset_id` | schema version, profile, attribute prefix, `data_origin`, `history_mode`, `timestamp_mode`, `source_timezone`, `snapshot_at`, currency |
| `records` | yes | `record_id` | one row per record (lead-deal): origin (`original` / `duplicate` / `reactivation`), parent, creation, route, source, channel, product, owners, reassignment, **state at the snapshot** (`current_stage`, `current_status`, `lost_reason`, `won_at`, `lost_at`), amounts |
| `stage_events` | no | `event_id` | stage history; `event_kind` = `transition`, `first_entry_milestone` or `reopen`; optional `seq` = source order within the record (0.1.1) |
| `activities` | yes | `activity_id` | calls, messages, emails, tasks, notes; `is_automated` is an optional **capability** column |
| `appointments` | no (capability) | `appointment_id` | booking, slot, outcome (`pending`, `held`, `no_show`, `rescheduled`, `cancelled`), reschedule and rebooking chains |
| `record_attributes` | no | (`record_id`, `attribute`) | profile attributes in long format with `value_type`; every key starts with the dataset prefix (`adm_`) |

Extension columns are allowed on `records`, `activities` and `appointments` only with the dataset prefix (`adm_…`). Any other undeclared column is rejected.

## 3. History modes: never infer history

| `history_mode` | Allowed `event_kind` | What can be measured |
|---|---|---|
| `full_event_history` | `transition`, `reopen` | first entries, re-entries, regressions, reopens, time in stage |
| `milestone_first_entry` | `first_entry_milestone` | first entry into each stage only |
| `snapshot_only` | none | state at the snapshot only |

Stage events are never derived from `current_stage`, appointments or activities. A milestone dataset keeps `event_kind = first_entry_milestone` and never produces entry counts, regressions, reopens or durations. In `snapshot_only`, no milestone exists; the state fields (`won_at`, `lost_at`) remain usable as state, not as history.

The generated admissions CSV only holds first-entry timestamps (`entered_*_at`, `enrolled_at`, `closed_lost_at`). It is therefore mapped as `milestone_first_entry`.

## 4. Timestamps

| `timestamp_mode` | Stored as | Allowed for |
|---|---|---|
| `naive_wall_clock` | `YYYY-MM-DD HH:MM:SS`, local wall clock; `source_timezone` is metadata only | `data_origin` = `synthetic` or `legacy` only |
| `utc` | `YYYY-MM-DDTHH:MM:SSZ` | any origin |

In `utc` mode, values with an offset are converted to UTC. Naive values are localised with `source_timezone`. An **ambiguous** local time (repeated hour) or a **non-existent** one (skipped hour) is an error, never a guess. The admissions dataset is synthetic and uses `naive_wall_clock` (Europe/Madrid as metadata). The admissions adapter accepts only `naive_wall_clock` in F2, because its SLA weekday and same-day definitions use the local wall clock.

## 5. Contract rules (neutral)

| Rule | Check |
|---|---|
| C01 | `event_kind` allowed by `history_mode`; `snapshot_only` has no stage events |
| C02 | at most one `first_entry_milestone` per record and stage |
| C03 | `transition` and `reopen` have `from_stage`; `first_entry_milestone` has none |
| C04 | timestamps follow `timestamp_mode`; `naive_wall_clock` only for synthetic or legacy data |
| C05 | no stage event, activity or booking after `snapshot_at` |
| C06 | `replaced_by_appointment_id` set exactly when the outcome is `rescheduled`, reciprocal with `rescheduled_from_appointment_id` |
| C07 | `is_automated` and `booking_is_automated` present in both tables or in neither |
| C08 (0.1.1) | `stage_events.seq`, when present, is unique per record and does not contradict `occurred_at` |
| C09 (0.1.1) | order within a record: `seq` if present, else `occurred_at`; equal timestamps without `seq` = indeterminate order (§11.4) |

The validator also checks the schema version, tables, columns, nullability, types, enums, patterns, primary keys and foreign keys. It is our own code, with no new dependency. Errors have stable codes (`E_…`).

## 6. Admissions profile

### 6.1 Mapping (`profiles/admissions/mapping_csv_v1.yaml`)

| CSV | Canonical |
|---|---|
| `lead_id`, `person_key`, `created_at`, `source`, `channel_group`, `program_alias`, `entry_path`, owners, `reassigned_at`, `pipeline_stage`, `lead_status`, `lost_reason`, `enrolled_at`, `closed_lost_at`, `list_price`, `net_price` | `records` (one-to-one) |
| `is_duplicate`, `is_reactivation` | `records.record_origin` (both true = error) |
| `reactivated_from_lead_id` | `records.parent_record_id` |
| `campaign_discount` + `one_time_discount` | `records.discount_amount` (aggregate) **and** `adm_campaign_discount`, `adm_one_time_discount` (kept separately) |
| `entered_*_at`, `enrolled_at`, `closed_lost_at` | `stage_events` (`first_entry_milestone`) |
| ILOC, nurture, post-interview fields, `payment_type`, `last_interview_outcome`, `candidate_profile` | `record_attributes` (`adm_…`) |
| activity rows with `activity_type = interview` | `appointments` (`direction = internal` and `sequence_name = booking` are constants, checked) |
| other activity rows | `activities` (`sequence_instance`, `business_day_index` as `adm_` extensions) |
| `is_synthetic`, `snapshot_date` | `dataset.data_origin`, `dataset.snapshot_at` |
| `first_human_attempt_at`, `first_connected_at`, `has_open_task`, `next_task_due_at`, `reassigned_flag` | not mapped: recomputed by the adapter with the F0 rules (§6.3) |

### 6.2 Profile rules (`profiles/admissions/rules.yaml`)

These rules belong to the admissions profile, not to the neutral contract. Error codes are `P_…`.

| Rule | Check |
|---|---|
| P01 | stages are the profile stages (`new_lead` … `enrollment_link_sent`, `closed_won`, `closed_lost`) |
| P02 | `entry_route` is `bot_booked` or `manual` (duplicates may have none) |
| P03 | a reactivation has `parent_record_id` |
| P04 | the parent exists, has the same `person_key`, was created earlier and is `closed_lost` with `future_intake` |
| P05 | originals and duplicates have no parent |
| P06 | `won_at` iff `closed_won`; `lost_at` iff `closed_lost` |
| P07 | amounts all set or all null; list − discount = net (to the cent) |
| P08 | `adm_campaign_discount` + `adm_one_time_discount` = `discount_amount` (to the cent) |
| P09 | `lost_reason` is a profile reason, on a `closed_lost` record |
| P10 | `current_status` is a profile status |

### 6.3 Adapter (`src/canonical/adapters/admissions.py`)

The adapter rebuilds the `leads` and `activities` frames with the same columns and dtypes as `checks.load`. On the generated data the round trip is exact (tested column by column). Derived fields follow the F0 rules:

| Field | Rule |
|---|---|
| `first_human_attempt_at` | first advisor outbound call or WhatsApp with `is_automated = False` |
| `first_connected_at` | first connected call, inbound activity or held appointment (its slot) |
| `has_open_task`, `next_task_due_at` | tasks with status `open` / `overdue`; earliest due date |
| `entered_<stage>_at` | first entry, from stage events only |
| `enrolled_at`, `closed_lost_at` | `records.won_at`, `records.lost_at` (state) |

When a capability is missing, the columns that depend on it stay empty. Every KPI that needs them is reported as not available (§7), so no number computed from missing inputs leaves the adapter.

## 7. KPI availability (`profiles/admissions/kpi_requirements.yaml`)

| Requirement | Met when | Reason code if missing |
|---|---|---|
| `stage_milestones` | `full_event_history` or `milestone_first_entry` | HM |
| `stage_transitions` | `full_event_history` | HF |
| `is_automated` | `activities.is_automated` present | AUT |
| `appointments` | `appointments` table present | APT |

A KPI that is not available is returned as `{"id", "status": "not_available", "reason", "missing"}` with **no** `value`, `numerator` or `denominator` key, so it can never be read as zero. If several requirements are missing, the reasons are joined (e.g. `HM+AUT`).

Since v1.2.1-f2 three situations are kept apart, in this order:

| Situation | Reason | Example |
|---|---|---|
| module absent (a table or column the KPI needs is missing) | `HM`, `HF`, `AUT`, `APT` | SLA without `is_automated` → `AUT`, even though `metrics.py` would compute 0 |
| zero denominator (inputs exist, denominator = 0) | `DEN0` (`missing: [nonzero_denominator]`) | forms / held interviews when no lead has a held interview |
| insufficient data (a median, mean or percentile has no observation) | `INSUF` (`missing: [observations]`) | sales cycle when no mature lead enrolled |

A true zero (numerator 0 over a positive denominator) remains an available value of 0. One KPI being not available never prevents computing the others.

The F2 catalogue has 31 indicators: 24 metrics and 7 history indicators (`first_entry`, `entry_count`, `regression_events`, `regression_rate`, `reopen_events`, `reopen_rate`, and `time_in_stage`, a capability with no expected value in the fixture). Requirements are declared for all 47 baseline metrics too.

| Variant of the hand fixture | available | not available |
|---|---|---|
| `v_full` (full history, all tables) | 31 | 0 |
| `v_milestone` | 25 | 6 (HF) |
| `v_snapshot` | 16 | 15 (9 HM, 6 HF) |
| `v_no_automated` | 23 | 8 (AUT) |
| `v_no_appointments` | 25 | 6 (APT) |

The generated admissions dataset behaves like `v_milestone`: the 24 metrics and `first_entry` are available, the 6 HF indicators are not.

## 8. History definitions (`src/canonical/history.py`)

Population: records with `record_origin = original`.

| Indicator | Definition | Needs |
|---|---|---|
| `first_entry` | records with ≥ 1 entry into each stage | milestones |
| `entry_count` | entries into each stage, re-entries included | full history |
| `regression_events` | transitions between open stages that go backwards | full history |
| `regression_rate` | regression transitions / all transition events | full history |
| `reopen_events` | reopen events (terminal → open stage) | full history |
| `reopen_rate` | records with ≥ 1 reopen / records that reached a terminal stage | full history |
| `time_in_stage` | median hours between entering a stage and the next stage event (last stage until the snapshot) | full history |

## 9. Tests and fixtures

- `tests/fixtures/canonical_handcalc/`: the official F2 fixture since v1.2.1-f2. It has **12 hand-built synthetic records** in five variants, with `expected.json` calculated by hand (source tables, derivations and a coverage inventory). It replaces the earlier 9-record draft (R1–R9), which is not reproduced; it is not the fixture approved in the plan. It is checked three ways: the expected-schema test, an independent recomputation that uses neither the generator, the adapter nor `metrics.py`, and the full path through the adapter and `metrics.py` for **all five variants**. Its provenance, including the dates and appointments changed in v1.2.0-f2, is recorded in `expected.json` (`provenance`).
- `tests/test_metrics_robustness.py` (v1.2.1-f2): zero denominators, no appointment table, no appointment from 2025-07-01, no observation for a statistic, module absent, and the DEN0 / INSUF / capability distinction.
- `tests/fixtures/mapping_errors/`: a valid three-lead CSV pair and 21 corruptions, each with its expected error code and stage (mapping, contract or profile).
- `tests/fixtures/timezones/`: daylight-saving edge cases in Europe/Madrid.
- `tests/test_regression_f1.py`: F0 and F1 byte-identical; 47 metrics through the canonical route equal to F0 and F1.

## 10. Robustness fix in `src/metrics.py` (v1.2.1-f2, authorised)

v1.2.0-f2 found that `src/metrics.py` raised an exception on three kinds of input that never occur in the generated data. The authorised fix changes no definition and no value:

| Defect (v1.2.0-f2) | Input | Fix |
|---|---|---|
| MP1 `ZeroDivisionError` in `forms_over_interviews_held` (two Python integers); `inf` possible in other ratios | no mature lead with a held interview | every ratio of `baseline_metrics` and `directional_rates` goes through `rate()` → NaN, reported as DEN0 |
| MP3 `TypeError` in `Context.bot_pre` (`Series.map` with an empty datetime mapper casts to float) | no appointment row | lookup with `reindex`, which keeps the datetime type |
| MP3b `TypeError` in `show_rate_per_lead` (empty result typed as string) | no appointment row | `Context.showlead` typed bool |
| MP4 `AttributeError` in `Context.personal_wa_appointments` (empty object column used as mask) | no held / no-show appointment from 2025-07-01 | typed boolean column |

On the generated data, the F1 metrics document generated **in memory** by the corrected `metrics.py` is byte-identical to `reports/f1/metrics_f1.json`; the check never writes to `reports/f1/` (it is frozen and its hashes are verified before and after each run). The 47 metrics equal F0 and F1 through both routes (tested). `src/metrics.py` is declared as the only authorised modification of a F1 source file; the regression tests pin its new hash.

## 11. Differences between the approved plan and the implemented contract

This revision documents the differences and adds only the optional `seq` column (contract `crm-canonical/0.1.1`, §11.4); nothing else in the contract changes.

### 11.1 Records

| Approved | Implemented | What it keeps | What it loses or changes |
|---|---|---|---|
| `is_duplicate` (flag) | `record_origin` ∈ {`original`, `duplicate`, `reactivation`} with `parent_record_id` | the duplicate flag (`record_origin = duplicate` ⇔ `is_duplicate = true`) and the reactivation flag in one column; the round trip back to `is_duplicate` / `is_reactivation` is exact (tested on the generated data) | a record cannot be both duplicate and reactivation (mapping error `M_ORIGIN_CONFLICT`); this never happens in the generated data, but a source with overlapping flags would need two columns |
| `status` ∈ {open, won, lost} | `current_status` (operational status of the profile) **and** the outcome derived from `current_stage` | see §11.2 | `current_status` is not the approved `status`: it is a different, finer field |
| `closed_at` | `won_at` + `lost_at` | `closed_at` = `won_at` if `closed_won`, `lost_at` if `closed_lost` (rule P06 guarantees exactly one, consistent with `current_stage`); the round trip to `enrolled_at` / `closed_lost_at` is exact | the closure type is stored twice (also in `current_stage`); neither form keeps earlier closures of a reopened record, which only exist in `stage_events` with full history |

### 11.2 `current_status` and the open / won / lost outcome

`current_status` is **not** a rename of the approved `status = open / won / lost`. It keeps the admissions profile's operational statuses at the snapshot: `new`, `working`, `iloc_sequence`, `nurture`, `closed_won` and `closed_lost` (rule P10). These are not outcomes: a lead in `nurture`, for example, is a deal already closed as lost (`current_stage = closed_lost`, `lost_reason = future_intake`) that is still receiving nurture messages.

The outcome is derived from `current_stage` and the profile's won and lost stages, never from `current_status` (`adapters/admissions.record_outcome`):

| `current_stage` | outcome |
|---|---|
| `closed_won` | won |
| `closed_lost` | lost (whatever the operational status, `nurture` included) |
| any open stage | open |

It is consistent with `won_at` / `lost_at` (P06). The test `tests/test_canonical_event_order.py` checks it on the fixture and on the generated data, where every `nurture` record is lost.

### 11.3 `stage_events`: approved specification and correspondence

Approved specification: key (`record_id`, `seq`); required `record_id`, `seq`, `stage`, `entered_at`, `event_kind`; optional `exited_at`, `changed_by_type`; when two events have the same timestamp, `seq` decides their order.

| Approved | Implemented (0.1.1) | Note |
|---|---|---|
| `record_id` | `record_id` | same |
| `seq` (required, part of the key) | `seq` (**optional**, unique per record when present; rule C08) | carried when the source provides an order; the admissions CSV does not (only first-entry timestamps), so the mapping emits no `seq` |
| key (`record_id`, `seq`) | key `event_id`; (`record_id`, `seq`) unique when `seq` exists | `event_id` is an extra identifier; for CSV milestones it is `<record_id>:<stage>` |
| `stage` | `to_stage` | the stage entered |
| `entered_at` | `occurred_at` | when the stage was entered |
| `event_kind` | `event_kind` ∈ {`transition`, `first_entry_milestone`, `reopen`} | same |
| — | `from_stage` (transition / reopen) | extra: each event states the stage it leaves, so regressions and reopens are identified per event without relying on order |
| `exited_at` (optional) | **not represented** | with full history and a determined order it equals the next event's `occurred_at` of the same record; in `milestone_first_entry` it is unknown; it is not stored |
| `changed_by_type` (optional) | **not represented** | who or what changed the stage is lost; no current KPI uses it |

### 11.4 Event order (crm-canonical/0.1.1, rules C08–C09)

- **When the source gives an order**, it is kept in `seq`. `seq` is unique per record and may not contradict `occurred_at` (a later `seq` never has an earlier timestamp). Datasets that carry `seq` declare `crm-canonical/0.1.1`. A `crm-canonical/0.1` dataset stays valid without `seq`.
- **Without `seq`**, events follow `occurred_at`. Events of the same record with the same `occurred_at` have an **indeterminate** order. It is never resolved by stage, `event_id` or file position (v1.2.1-f2 used `event_id` as a tie-break inside `time_in_stage`; that was removed).
- **What depends on order:** only `time_in_stage`. With an indeterminate order it is returned as `not_available` with reason `ORD` (`missing: [event_order]`). `first_entry`, `entry_count`, regressions and reopens do not depend on order, because each event carries `from_stage` and `to_stage`. `tests/test_canonical_event_order.py` proves this with simultaneous events, shuffled rows and renamed ids.

## 12. How to run

```bash
python scripts/map_to_canonical.py      # writes build/canonical/admissions/ (outside the tree manifest)
pytest -q                               # all tests, F0/F1/F2
python scripts/f2_run.py --check        # clean run, F0/F1 frozen, 47 metrics, five variants, F2 manifest
```
