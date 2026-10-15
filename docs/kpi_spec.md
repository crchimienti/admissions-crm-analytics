**Language:** English | [Español](kpi_spec.es.md)

# Declarative KPI specification `kpi-spec/0.1` (F3.0, `v1.3.1-f3`)

> All data is **synthetic**. F3.0 starts separating KPI definitions from admissions-specific code. Eight KPIs are declared in a small configuration and evaluated on canonical datasets by an engine that runs **in parallel** with `src/metrics.py`. `src/metrics.py` remains the official reference and is not modified. This is not a universal framework: admissions profile only, no portability claim, no CRM, no real data.

## 1. Pieces

| File | Role |
|---|---|
| [`schema/kpi_spec_v0.1.yaml`](../schema/kpi_spec_v0.1.yaml) | the closed language: keys, operations, filters, ratio relations, error codes, unavailability reasons |
| [`profiles/admissions/kpis.yaml`](../profiles/admissions/kpis.yaml) | the eight admissions KPIs: fields, populations, KPIs |
| `src/kpispec/spec.py` | loading and validation (first violation → `KpiSpecError` with a `K_*` code; nothing invalid is evaluated) |
| `src/kpispec/fields.py` | field resolution: values, or the reason a field is not available; declared domains are enforced |
| `src/kpispec/engine.py` | populations, filters and operations; does not import `src/metrics.py`, directly or indirectly (the adapter loads it only for the metrics route) |

## 2. The language (closed)

**Operations (5):** `count`, `share`, `ratio`, `duration_stat` (median, mean or p90 with linear interpolation, in hours or days), `field_stat` (mean; in the catalogue, not used in F3.0). Numerator and denominator follow the F0 convention:

| Operation | value | numerator | denominator |
|---|---|---|---|
| `count` | n | n | null |
| `share` | subset / population | n subset | n population |
| `ratio` | population A / population B | n A | n B |
| `duration_stat`, `field_stat` | statistic | null | n observations |

**Filters (AND only):** `equals`, `in`, `not_null`, `is_null`, `age_at_least_days`, `created_before_snapshot_minus_hours`, `at_or_before_snapshot`, `weekday_in` (Monday = 0), `duration_le_hours` (a null end never matches). There are no expressions, no OR and no embedded code: keys such as `or`, `expr`, `formula`, `code`, `lambda`, `eval` or `sql` are rejected (`K_FORBIDDEN_KEY`).

**Populations** have a `unit` (`lead` or `appointment`) or are defined `from` another population plus more filters. A filter may only read fields of the population's unit (or the dataset).

## 3. Fields: nothing is assumed available

Each field declares its source and how it can be missing:

| Source form | Missing table / column gives |
|---|---|
| `records.<col>`, `dataset.<col>` | the field's `if_missing` (FLD for the admissions fields) |
| `records.<col>` `via: appointments.record_id` | `if_missing` (APT) if there are no appointments; FLD if the records column is absent |
| `appointments.<col>` | `if_missing` (APT) if the table is absent; FLD if only the column is absent |
| `stage_first_entry.<stage>` | `if_missing: HM` when the dataset has no stage milestones; `if_missing: HF` when it has no full event history (milestones are not enough). The eight F3.0 KPIs only use HM. |
| `profile.<function>` | each entry of `needs` is checked: e.g. `first_human_attempt` needs `activities.is_automated` (AUT) and `actor_type`, `direction`, `activity_type` (FLD) |

Fields may declare their domain (`values`, `nullable: false`). A value outside it, or a null where it is not allowed, raises `K_FIELD_VALUE`: the run stops instead of letting a record into a population silently.

## 4. Order of decisions and reasons

1. Every field the KPI reads (its own and those of all populations it is defined from) is resolved. Any missing field makes the KPI `not_available` with the joined reasons in order of appearance and the **exact list of missing fields**: `FLD`, `HM`, `HF`, `AUT`, `APT` (e.g. `FLD+AUT`).
2. Otherwise the operation is computed.
3. An undefined result is `DEN0` (zero denominator, `missing: [nonzero_denominator]`) or `INSUF` (no observation, `missing: [observations]`). `ORD` (indeterminate event order) exists in the catalogue but no F3.0 KPI depends on order.
4. A true zero (numerator 0 over a positive denominator, or a count of 0) is an available 0.

A `not_available` result is exactly `{id, status, reason, missing}`; it never carries `value`, `numerator` or `denominator`. One KPI being not available never prevents the others.

`FLD` (approved in F3.0) means a required field or attribute is not provided by the load or the profile. It does not cover null values in individual records: those are handled by the filters.

## 5. Ratio contract

Checked when the configuration is loaded; a violation is a configuration error and nothing is evaluated.

- Both populations must have the **same unit** (`K_RATIO_UNIT`).
- `relation` is mandatory (`K_RATIO_RELATION_MISSING`):

| relation | Requirement | Meaning |
|---|---|---|
| `subset_of` | the numerator is defined `from` the denominator | the numerator is contained in the denominator (also asserted at run time) |
| `same_base` | both are defined `from` the same base population | different filters on one base; the numerator need not be a subset; the value may exceed 1 |
| `independent_allowed` | a written `justification` (`K_RATIO_JUSTIFICATION`) | different bases with the same unit |

A relation that does not match how the populations are defined gives `K_RATIO_RELATION`. A ratio is not assumed to be a funnel conversion. `forms_over_interviews_held` is `same_base` (both from `mature`): its F0 definition does not require leads with a form to have a held interview, even though that happens to hold in the generated data. Valid and invalid examples are tested in `tests/test_kpi_spec_schema.py`.

## 6. Eligibility (admissions profile rule)

F0 defines an eligible lead as `is_duplicate = false` and `is_reactivation = false`. The admissions mapping sets `record_origin = duplicate` when `is_duplicate`, `reactivation` when `is_reactivation`, and `original` otherwise, and rejects a row with both flags (`M_ORIGIN_CONFLICT`). Therefore, **for the admissions profile**:

`record_origin = original` ⇔ `is_duplicate = false` and `is_reactivation = false`.

This is a rule of the admissions profile (the `eligible` population in `profiles/admissions/kpis.yaml`), not of the engine, which knows nothing about eligibility. `tests/test_kpi_eligibility.py` checks the equivalence on the generated data (against the F0 loader), on the canonical path (adapter frames) and on the fixture. `record_origin` is declared with its domain and as non-nullable:
- an unknown origin is rejected by the contract (`E_ENUM`) and by the engine (`K_FIELD_VALUE`);
- a null origin raises `K_FIELD_VALUE`;
- a missing origin field gives `FLD` for every KPI.

No record enters `eligible` silently.

## 7. The eight F3.0 KPIs

| KPI | Operation | Unit | Population | Requires |
|---|---|---|---|---|
| `eligible_leads` | count | lead | eligible | `record_origin` |
| `share_manual_route` | share | lead | eligible | + `entry_route` |
| `main_kpi_interviews_held_over_opportunities` | share | lead | mature (maturity) | `record_origin`, `created_at`, `snapshot_at`, `held_entered_at` (HM) |
| `show_rate_per_appointment` | share | appointment | held + no-show eligible appointments | appointment fields (APT), `snapshot_at` |
| `forms_over_interviews_held` | ratio `same_base` | lead | mature with form / mature with held | + `form_entered_at`, `held_entered_at` (HM) |
| `sla_first_attempt_24h_manual_weekend` | share (SLA, calendar) | lead | manual, 24 h window, Sat–Sun | + `entry_route`, `first_human_attempt_at` (AUT) |
| `first_response_p90_hours` | duration_stat p90 | lead | manual, 24 h window | + `first_human_attempt_at` (AUT) |
| `sales_cycle_median_days` | duration_stat median | lead | mature enrolled | `record_origin`, `created_at`, `snapshot_at`, `won_at` |

On the generated data the eight are identical to F0, F1, F2 and `src/metrics.py` (values at 6 decimals, numerators, denominators and descriptive fields; `tests/test_kpi_regression.py`). On the official 12-record fixture:

| Variant | available / not available | not available |
|---|---|---|
| `v_full` | 8 / 0 | — |
| `v_milestone` | 8 / 0 | — |
| `v_snapshot` | 6 / 2 | main KPI, forms / held (HM) |
| `v_no_automated` | 6 / 2 | weekend SLA, p90 first response (AUT) |
| `v_no_appointments` | 7 / 1 | per-appointment show rate (APT) |

## 8. Limits

- `time_model` is `naive_wall_clock` only. UTC instants and local-calendar rules arrive with **F3.5**, which is planned and not implemented.
- Only the admissions profile and its eight KPIs are configured; the other 27 parametrisable KPIs are F3.1 (not authorised yet), and 12 KPIs stay profile functions in `src/metrics.py`.
- No cohort, month or segment breakdowns; `src/metrics.py` still produces those and remains the official reference.
- No readiness for real data or CRM connections is claimed.

## 9. How to run

```bash
pytest -q tests/test_kpi_*.py tests/test_regression_f2.py
python scripts/f3_run.py --check     # clean run, frozen F0/F1/F2, eight KPIs vs references, five variants, F3 manifest
```
