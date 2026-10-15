**Language:** English | [Español](analytical_decisions.es.md)

# Analytical decisions

> A short summary for readers of the repository. The authoritative definitions are in [`kpi_definitions.md`](kpi_definitions.md), [`assumptions.md`](assumptions.md), [`canonical_schema.md`](canonical_schema.md) and [`kpi_spec.md`](kpi_spec.md); if this page and those documents ever disagree, those documents apply. All values in this repository are synthetic.

## 1. Who is counted (populations and denominators)

| Decision | Rule | Why |
|---|---|---|
| Eligible lead | `is_duplicate = false` and `is_reactivation = false`; reactivations are reported separately | duplicates and returning leads would inflate the base |
| Main KPI denominator | **all** mature eligible leads, from both routes | the CRM's Opportunity stage would leave out the bot route, which books interviews directly |
| Main KPI numerator | mature eligible leads with at least one **held** appointment | a booked or no-show appointment is not an interview |
| One unit per metric | lead-level and appointment-level metrics are never mixed: show rate is reported both **per appointment** and **per lead** | they answer different questions |
| Eligible appointment | of an eligible lead, not replaced by a reschedule, scheduled no later than the snapshot | a rescheduled appointment would be counted twice |
| SLA denominator | eligible manual leads created at least 24 h before the snapshot; leads with no attempt **stay in the denominator** | dropping them would hide the worst cases |
| First-response percentiles | only leads with an attempt (the observed durations) | a duration cannot be computed without an end |

## 2. When (cohort, period and snapshot)

- **Snapshot.** One fixed cut-off: 2025-12-31 23:59. Every state ("open", "overdue") is measured at that moment.
- **Cohort.** The month of `created_at`. Conversions are measured on **mature** leads only: `snapshot − created_at ≥ 60 × 24 h`, per lead, with full timestamps. Partial and immature cohorts are labelled and never compared with mature ones.
- **Period.** The month of the event (appointment slot, activity, enrollment), used for show rate, workload and governance.
- **Hours.** SLA and follow-up use **calendar hours** (a documented v1 decision); interview-recovery cadence uses business days. Calendar hours include nights and weekends, which is why weekend arrivals score lower in this scenario.
- **Time zone.** The synthetic data uses local wall-clock timestamps. UTC instants and local-calendar rules are a future phase (F3.5), not implemented.

## 3. Missing data and anomalies

- **Missing is not zero.** When a dataset lacks what a KPI needs, the KPI is `not_available` with a reason and the exact missing fields, and carries no value, numerator or denominator. Reasons: `HM` (no stage milestones), `HF` (no full stage history), `AUT` (no automation flag), `APT` (no appointments), `FLD` (field not provided), `DEN0` (zero denominator), `INSUF` (no observations), `ORD` (event order undetermined). A true zero stays an available 0.
- **A null in one row is not a missing field.** It is handled by the KPI's rule (for example, a lead with no attempt fails the SLA filter and stays in its denominator).
- **No invented history.** Stage history is never inferred from the current stage, appointments or activities.
- **Unknown values stop the calculation.** A value outside a field's declared domain (for example an unknown record origin) is a data error, not a silent exclusion.
- **Anomalies are known by design.** The generator injects data-quality anomalies and lists them in `data/dq_ground_truth.csv`; each detection rule is compared with that ground truth in the same unit, and mutation tests prove the checks can fail.

## 4. What the numbers do not show

Synthetic results reflect the scenario parameters, not a real team or market. No causal effect is claimed: interventions such as the personal WhatsApp channel have zero programmed effect, and any apparent difference is association. The advisor comparison is exploratory. Full list of limits: [`assumptions.md` §4](assumptions.md).
