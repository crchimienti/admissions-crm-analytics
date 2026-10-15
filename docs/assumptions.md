**Language:** English | [Español](assumptions.es.md)

# Project assumptions (v1) — approved

> **Notice.** All data in this project is **synthetic**. No figure in this document is a historical observation or a finding. The values in section 3 are **synthetic scenario parameters**: arbitrary values chosen so the scenario can be analysed, not realistic, calibrated or expected rates. They are stored in a central configuration (`config/simulation_params.yaml`) and generated with a fixed seed (42).

## 0. Summary of the four categories

| # | Category | Contents | Origin | How it may be cited |
|---|---|---|---|---|
| 1 | Operational context provided | Process structure, stages, CRM rules, ILOC cadence, indicative ranges | Real professional experience, anonymised | "The process is based on real, anonymised operational experience" |
| 2 | Confirmed analytical decisions | KPI definitions, cohorts, SLA, calendar and pricing treatment | Design decisions of this project | "Project analytical definition", never "official KPI" |
| 3 | Synthetic scenario parameters | Rates, mixes, timings, anomalies and discount probabilities | Chosen arbitrarily for the simulation | "Synthetic scenario parameter"; never as data, a realistic rate or a result |
| 4 | Interpretation limits | What cannot be concluded from this data | Consequence of 1–3 | Must appear in the README and in conclusions |

---

## 1. Operational context provided (real, anonymised)

| Area | Context |
|---|---|
| Business | B2C admissions for online certificates, for healthcare and non-healthcare profiles |
| Acquisition | New brand: social media and webinars. Other channels (web/direct, organic, referral, events, partners) are plausible for more established brands |
| Team | 5–6 full-cycle advisors and 1 supporting Team Lead (programme knowledge and academic coordination) |
| Assignment | Automatic, based on calendar availability |
| Indicative volume | 100–120 leads/month per advisor and 600–800 per team; more than 150 per advisor was considered excessive. Context ranges, not quotas |
| Stages | New Lead → Opportunity → Interview Booked → Interview Held → Application Form Completed → Enrollment Link Sent → Enrolled / Closed Won; Closed Lost |
| Bot route | If the bot booked on entry, the lead moved from New Lead to Interview Booked |
| Manual route | If the bot did not book, the lead moved to Opportunity for advisor follow-up |
| No-show | Did not change the stage: the lead remained in Interview Booked |
| Central milestone | The admission interview; every eligible lead should move towards it |
| Loss reasons | ILOC, financial reasons, official-qualification concern, future intake |
| ILOC | BD0 call (+ WhatsApp and email 1 if unanswered); BD1 no action; BD2 call; BD3 email 2; BD4 call (+ WhatsApp); BD5 email 3; BD6 close as ILOC. Stops if the candidate replies or books |
| After no-show | The bot tries to reschedule; ILOC may start a couple of days later |
| Reminders | Bot WhatsApp confirmation, automated reminders (email/bot) and, later, personalised advisor WhatsApp |
| Post-interview | Email with offer, catalogue and link; the bot requests the form at 24 h and 48 h; manual follow-up on the form |
| Closing | Enrollment and payment link; confirmation email after payment |
| Governance | Same-day contact (max. 24 h); reassignment if no contact in 24 h; alert if no follow-up 24–48 h after the interview; no closing without a reason; no opportunity without a next task; no stage change without a record |
| Reference pricing | Usual ticket €2,000–2,500; list price €3,200; campaign discount €600, €500 or €350; extra 15 % for one-time payment, applied after the campaign discount |
| Observed issues | Late response, low contactability, stages not updated, no-shows, inconsistent post-interview follow-up, missing nurture emails, opportunities without a next task, stalled leads (especially in September) |

---

## 2. Confirmed analytical decisions

| Topic | Decision |
|---|---|
| Dimensions | `pipeline_stage`, `interview_outcome`, `lead_status` and `lost_reason` are independent; no-show is recorded only in `interview_outcome` |
| Unit | One synthetic `lead_id` per lead-deal and a synthetic `person_key` for every lead, used to detect duplicates and link reactivations (§2.4) |
| Eligible lead | `is_duplicate = false` and `is_reactivation = false`. Reactivations are analysed separately |
| Main KPI | **Interviews held / opportunities** = mature eligible leads with at least one `held` appointment / **all mature eligible leads in the cohort (both routes)**. It is a lead-level metric; the Opportunity stage alone is not used (§2.6) |
| Separate metrics | Conversion to held interview (all leads, plus split by route), conversion to held interview on the manual route, show rate of booked appointments |
| Per-appointment show rate | `held` appointments / `held` + `no_show` appointments. It is an appointment-level metric, with the exclusions in §2.3 and §2.6 |
| Cohorts | Conversions by `created_at` month; activity, closures and workload by period |
| Maturity | Lead-level rule: mature if `snapshot_date − created_at ≥ 60 days` (analytical assumption). Cohort conversions use mature leads only (§2.5) |
| SLA | Manual route: first human attempt. Bot route: pre-interview confirmation and contact, analysed separately. Project analytical definition, not an official historical KPI |
| First response | In calendar hours (documented v1 decision) |
| ILOC calendar | Business days Monday–Friday, no holidays in v1; BDn is the n-th business day from BD0 (§2.2) |
| ILOC duration | Depends on the day BD0 starts; reported in business days and in calendar days (§2.2) |
| ILOC after no-show | Starts after 2 business days without a response |
| Interviews without a booking | Not included in v1 |
| Pricing (synthetic rule) | One-time payment: (3,200 − campaign discount) × 0.85. Instalments: 3,200 − campaign discount. Not a reconstruction of real sales |
| Finance | List price, campaign discount, one-time discount and `net_price` kept separate. No payments, collections, CAC or ROI |
| Attribution | Each activity is attributed to whoever performed it. All five advisors share the same base parameters; advisor conversion (by first and by current owner) is exploratory only |
| Reactivation | New lead-deal with the same `person_key` and `is_reactivation = true`. A technical convention, not a claim about the real CRM |
| Interventions | Zero effect for personalised WhatsApp, training and reassignment |
| Simulated team | 5 advisors (ADV_01–ADV_05) and 1 Team Lead with no own portfolio, no joiners or leavers |
| Period | 12 synthetic months with a fixed seed; no historical dates reproduced |

### 2.1 States: allowed values and consistency rules

| Dimension | Level | Allowed values |
|---|---|---|
| `pipeline_stage` | lead (current stage) | `new_lead` (New Lead) · `opportunity` (Opportunity) · `interview_booked` (Interview Booked) · `interview_held` (Interview Held) · `form_completed` (Application Form Completed) · `enrollment_link_sent` (Enrollment Link Sent) · `closed_won` (Enrolled / Closed Won) · `closed_lost` (Closed Lost) |
| `interview_outcome` | appointment (`activities`, `interview` rows) | `pending` · `held` · `no_show` · `rescheduled` · `cancelled` |
| `last_interview_outcome` | lead | `pending` · `held` · `no_show` · `cancelled` · null if no appointments (never `rescheduled`) |
| `lead_status` | lead | `new` · `working` · `iloc_sequence` · `nurture` · `closed_won` · `closed_lost` |
| `lost_reason` | lead | `iloc` · `financial` · `official_qualification` · `future_intake` · null |

Meaning of `lead_status`:
- `new`: open, manual route, no human attempt yet.
- `working`: open and being worked (includes bot-route leads with an appointment).
- `iloc_sequence`: open with the ILOC sequence active.
- `nurture`: deal closed as lost for `future_intake` that is in the nurture sequence.
- `closed_won`: enrolled.
- `closed_lost`: closed as lost, with no active nurture.

| # | Rule |
|---|---|
| R1 | `pipeline_stage = closed_won` ⇔ `lead_status = closed_won` ⇔ `enrolled_at` not null. In that case `lost_reason` is null and the pricing fields are filled |
| R2 | `pipeline_stage = closed_lost` ⇔ `lead_status` ∈ {`closed_lost`, `nurture`} ⇔ `closed_lost_at` not null |
| R3 | `lost_reason` not null ⇒ `pipeline_stage = closed_lost`. Normal rule: `closed_lost` ⇒ `lost_reason` not null. **Deliberate exception:** a `closed_lost` with a null `lost_reason` is an injected anomaly (§3.8). It can only occur with `lead_status = closed_lost`, never in `nurture` or in ILOC closures (R6) |
| R4 | `lead_status = nurture` ⇒ `pipeline_stage = closed_lost` and `lost_reason = future_intake` |
| R5 | `lead_status = iloc_sequence` ⇒ `pipeline_stage` ∈ {`opportunity`, `interview_booked`}, `iloc_started_at` not null and `iloc_ended_at` null |
| R6 | `lost_reason = iloc` ⇒ `iloc_end_reason = closed_iloc` and `closed_lost_at` on the sequence's BD6 |
| R7 | `lead_status = new` ⇒ manual route, `pipeline_stage` ∈ {`new_lead`, `opportunity`} and `first_human_attempt_at` null |
| R8 | Bot route ⇒ `entered_opportunity_at` null. Manual route ⇒ `entered_opportunity_at` not null |
| R9 | Stage timestamps do not decrease in funnel order; `pipeline_stage` matches the last stage reached; `closed_won` and `closed_lost` are terminal |
| R10 | A no-show does not change the stage: if the last appointment is `no_show` and the lead is still open, `pipeline_stage = interview_booked` |
| R11 | `last_interview_outcome` is the outcome of the last non-replaced appointment; it can only be `pending` if that appointment has `interview_scheduled_for` > `snapshot_date` (§2.3). At least one `held` appointment exists ⇔ `entered_interview_held_at` not null |
| R12 | `payment_type`, `list_price`, `campaign_discount`, `one_time_discount` and `net_price` are filled only if `pipeline_stage = closed_won` |
| R13 | Rows with `is_duplicate = true` are subject only to the identity rules (§2.4). They are excluded from R5–R11, from KPIs and from governance indicators |

**Deal lost for `future_intake` that enters nurture.** It is represented by three dimensions without mixing them: `pipeline_stage = closed_lost` (the deal is closed), `lost_reason = future_intake` (why it was lost) and `lead_status = nurture` (what is done with it operationally). Nurture activities are logged on the same `lead_id`.
- If the person reactivates, the original deal moves to `lead_status = closed_lost` (leaves nurture and keeps its `lost_reason`) and a new `lead_id` is created with the same `person_key` and `is_reactivation = true`. A person never has a deal in nurture and an open deal at the same time.
- If the nurture window ends without reactivation, the deal moves to `lead_status = closed_lost`.
- `new_lead` is a transient stage: the lead moves to `opportunity` or `interview_booked` as soon as the bot attempts to book.

### 2.2 ILOC sequence calendar

BDn is the n-th business day of the sequence counting from BD0: business days are counted (Monday–Friday, no holidays in v1), never calendar days.
- BD1 is the business day immediately after BD0, never a weekend day. If BD0 is a Friday, BD1 is the following Monday.
- Saturdays and Sundays are not sequence days and generate no activity.
- An activity is created only when the step has a scheduled action: BD0, BD2, BD3, BD4 and BD5. BD1 is a business day with no scheduled action. BD6, the sixth business day after BD0, is the day of the ILOC closure.
- Manual route: BD0 is the day of the first call attempt. If the lead arrives on Saturday or Sunday, BD0 is the following Monday.
- After a no-show: BD0 is the second business day after the day of the no-show.

**Counting convention.** "Elapsed days" is the difference between dates (end date − start date). "Dates included" counts both ends (elapsed days + 1). Reports use elapsed days unless stated otherwise.

| BD0 | BD5 (last action) | BD6 (ILOC closure) | BD0→BD5: elapsed / included | BD0→BD6: elapsed / included |
|---|---|---|---|---|
| Monday | following Monday | following Tuesday | 7 / 8 | 8 / 9 |
| Tuesday | following Tuesday | following Wednesday | 7 / 8 | 8 / 9 |
| Wednesday | following Wednesday | following Thursday | 7 / 8 | 8 / 9 |
| Thursday | following Thursday | following Friday | 7 / 8 | 8 / 9 |
| Friday | following Friday | Monday of the week after | 7 / 8 | 10 / 11 |

- Without holidays, the BD0–BD5 action window always covers 8 dates included (7 elapsed days). This is the reading consistent with the operational context ("up to 8 calendar days").
- The BD6 closure falls 8 elapsed days after BD0 (9 dates included), or 10 elapsed days (11 dates included) if BD0 is a Friday.
- If the lead arrives at the weekend and the first attempt is on Monday, the time until BD0 is added: 2 elapsed days from Saturday and 1 from Sunday. From arrival to BD6 there are 10 elapsed days for a Saturday arrival and 9 for a Sunday arrival.
- Sequence duration is reported in business days and in elapsed days.

### 2.3 Appointments and rescheduling

Each appointment is an `activities` row with `activity_type = interview`. `activity_at` is the booking time and `interview_scheduled_for` is the appointment time.

| `interview_outcome` | Terminal outcome? | Treatment |
|---|---|---|
| `held` | Yes | Counts in the show rate |
| `no_show` | Yes | Counts in the show rate. The lead stays in `interview_booked` |
| `cancelled` | Yes | Excluded from the show rate and reported separately (cancellation rate) |
| `rescheduled` | **No.** It always generates a replacement appointment | The replaced appointment does not enter any show-rate denominator. It stores `replaced_by_activity_id`; the replacement stores `rescheduled_from_activity_id` |
| `pending` | No. It is a future appointment | Only valid if `interview_scheduled_for` > `snapshot_date`. Excluded from the show rate |

- **Rescheduling:** the appointment is moved before it takes place and a replacement is always created, which may stay `pending` if its date is after the cut-off. Original and replacement form a chain, and only the last appointment in the chain can have a terminal outcome.
- **New booking after a no-show or cancellation:** not a replacement. The `no_show` or `cancelled` appointment keeps its terminal outcome and the new appointment stores `rebooked_after_activity_id`.
- **Cut-off date:**
  - Every appointment with `interview_scheduled_for` ≤ `snapshot_date` gets a terminal outcome or `rescheduled`.
  - Appointments dated after the cut-off stay `pending`, because nothing after the cut-off is recorded.
  - A past appointment still `pending` (overdue without an outcome) is not generated in v1. If one appears, it is a generator logic error and the test fails.
- **Per-appointment show rate** = `held` appointments / (`held` + `no_show`) appointments, only appointments with a null `replaced_by_activity_id` and `interview_scheduled_for` ≤ `snapshot_date`.
- **Cancellation rate** = `cancelled` appointments / non-replaced appointments with a terminal outcome (`held`, `no_show`, `cancelled`).
- **Per-lead show rate** = leads with ≥1 `held` appointment / leads with ≥1 non-replaced appointment whose outcome is `held` or `no_show`.
- `activities` fields linking appointments: `replaced_by_activity_id`, `rescheduled_from_activity_id` and `rebooked_after_activity_id`.

### 2.4 Identity: `person_key`, duplicates and reactivations

- Every lead has a synthetic `person_key` (`P000001`, …). It replaces any personal data: no names, emails or phone numbers are generated.
- **Original lead:** a person's first row, with `is_duplicate = false` and `is_reactivation = false`.
- **Duplicate:** a second entry for the same person, created 0–14 days after an earlier non-duplicate row of theirs, not coming from nurture. Same programme, same or different source. It has `is_duplicate = true`, stage `new_lead`, `lead_status = new` and no activities.
- **Reactivation:** a row with the same `person_key` as an earlier deal closed for `future_intake` in nurture, created 30–150 days later. It has `is_reactivation = true` and `is_duplicate = false`.
- **Detection rule**, reproducible from the data: sorting by `person_key` and `created_at`, a row is a duplicate if it is not a reactivation and there is an earlier row for the same person with `is_duplicate = false` created ≤ 14 days before. Tests check that the `is_duplicate` flag matches this rule exactly.
- Apart from duplicates and reactivations, the generator creates no more than one row per person.
- Reactivations do not count as new leads: cohort KPIs use eligible leads only and reactivations are reported separately.

### 2.5 Lead and cohort maturity

- **Mature lead:** `snapshot_date − created_at ≥ 60 days`, computed with full timestamps (60 × 24 h).
- **Monthly cohort** (by `created_at` month):
  - `mature`: 100 % of its eligible leads are mature.
  - `partial`: only some of its eligible leads are mature.
  - `immature`: none of its eligible leads is mature.
- Cohort conversions are computed with mature leads only. For a partial cohort, the fraction included in the calculation is shown, and that cohort is not compared with mature ones. A month is not labelled mature just because some of its leads have reached 60 days.
- With the proposed cut-off (2025-12-31 23:59), the rule is equivalent to a creation threshold of 2025-11-01 23:59 (cut-off − 60 × 24 h).
- Each cohort's label is not declared in advance: it is computed from the share of that cohort's eligible leads that are mature. The notebook shows, for each month, eligible leads, mature leads, the share and the resulting label.
- Period indicators (activity, workload, governance) do not depend on maturity.

### 2.6 Interview metrics: unit of count

Lead-level metrics count leads and appointment-level metrics count appointments. Appointment outcomes are never used as if they were lead counts.

| Metric | Unit | Numerator | Denominator | Time basis |
|---|---|---|---|---|
| **Main KPI: interviews held / opportunities** | lead | mature eligible leads with at least one `held` appointment | all mature eligible leads from both routes | cohort by `created_at` |
| Conversion to held interview by route | lead | the same, filtered by `entry_path` | mature eligible leads on that route | cohort |
| **Per-appointment show rate** | appointment | `held` appointments | `held` + `no_show` appointments | month of `interview_scheduled_for` |
| Per-lead show rate | lead | leads with at least one `held` appointment | leads with at least one eligible appointment whose outcome is `held` or `no_show` | cohort |
| Cancellation rate | appointment | `cancelled` appointments | eligible appointments with outcome `held`, `no_show` or `cancelled` | month of `interview_scheduled_for` |

**Eligible appointment:** an appointment of an eligible lead (no duplicates), with a null `replaced_by_activity_id` (not replaced by rescheduling) and `interview_scheduled_for` ≤ `snapshot_date`. Therefore `rescheduled` and `pending` appointments are excluded; `cancelled` ones only enter the cancellation rate.

---

## 3. Synthetic scenario parameters (pending approval)

All values in this section are **synthetic scenario parameters**: arbitrary, chosen so the scenario can be analysed. They are not realistic, calibrated or expected rates. They are stored in `config/simulation_params.yaml` and generated with seed 42.

### 3.1 Period, seed and volume

| Parameter | Proposed value | Note |
|---|---|---|
| Calendar | 2025-01-01 to 2025-12-31 | A calendar year is used only to get real weekdays; it does not correspond to any historical period |
| Cut-off (`snapshot_date`) | 2025-12-31 23:59 | Leaves an open pipeline and immature November and December cohorts, so governance can be measured |
| Seed | 42 | |
| Scenario monthly volume: new eligible leads (team) | Jan 640 · Feb 620 · Mar 620 · Apr 600 · May 620 · Jun 600 · Jul 600 · Aug 600 · **Sep 780** · Oct 680 · Nov 640 · Dec 600 | Poisson noise, clipped to [600, 800]. Duplicates (§3.8) and reactivations (§3.7) are generated separately and do not count in this volume |
| Day-of-week distribution | Mon–Fri weight 1.0 · Sat 0.5 · Sun 0.6 | |
| Arrival hour | Peaks 10–14 h and 18–22 h; ~15 % between 22–08 h | Relevant for the calendar-hours SLA |
| Assignment weight per advisor | ADV_01 0.23 · ADV_02 0.21 · ADV_03 0.20 · ADV_04 0.19 · ADV_05 0.17 | Scenario assignment parameter. It does not represent a real distribution and says nothing about individual performance |
| Advisor working hours | Mon–Fri 09:00–19:00 | The bot runs 24/7 |

**Expected workload check per advisor and month**

- **Workload definition:** eligible leads (no duplicates or reactivations) assigned by `first_owner_id` and `created_at` month. Reactivations are reported in a separate column. Reassignments do not change workload, because it is measured by first owner.
- **Formula:** expected workload = scenario monthly volume × advisor assignment weight. These are expected values before randomness. The notebook will show the realised workload.

| Scenario volume | Months | ADV_01 (0.23) | ADV_02 (0.21) | ADV_03 (0.20) | ADV_04 (0.19) | ADV_05 (0.17) | Sum |
|---|---|---|---|---|---|---|---|
| 600 | Apr, Jun, Jul, Aug, Dec | 138.0 | 126.0 | 120.0 | 114.0 | 102.0 | 600 |
| 620 | Feb, Mar, May | 142.6 | 130.2 | 124.0 | 117.8 | 105.4 | 620 |
| 640 | Jan, Nov | 147.2 | 134.4 | 128.0 | 121.6 | 108.8 | 640 |
| 680 | Oct | **156.4** | 142.8 | 136.0 | 129.2 | 115.6 | 680 |
| 780 | Sep | **179.4** | **163.8** | **156.0** | 148.2 | 132.6 | 780 |

- Expected values above 150 occur in October (ADV_01) and September (ADV_01–03). They do not depend only on the September peak: the uneven assignment weight also produces them.
- ADV_01 has expected values of 138.0–147.2 for the rest of the year. With random variation (standard deviation of roughly √workload, about 12 leads per advisor per month), realised workload can exceed 150 in those months too.
- Most expected values exceed 120. This follows from combining 5 advisors with a team volume of 600–800; it is neither a finding nor a performance indicator.
- Alternative: with equal weights (0.20), expected workload is 120.0–128.0 in most months, 136.0 in October and 156.0 for everyone in September.

### 3.2 Sources, routes, profiles and programmes

| `channel_group` | Weight | % bot route | Conversion modifier |
|---|---|---|---|
| paid_social | 45 % | 25 % | 0.85 |
| webinar | 25 % | 40 % | 1.15 |
| web_direct | 12 % | 35 % | 1.05 |
| organic | 8 % | 30 % | 1.00 |
| referral | 5 % | 30 % | 1.25 |
| event | 3 % | 20 % | 1.00 |
| partner | 2 % | 20 % | 1.10 |

- The overall bot-route share comes out at about 30 %, as a result of the weights in the table.
- The conversion modifier is multiplicative on contact, booking after contact, form and enrollment. Probabilities are capped at 0.95.

| Parameter | Proposed value |
|---|---|
| `candidate_profile` | healthcare 55 % · non-healthcare 45 % |
| Programmes | PRG_A, PRG_B (healthcare-oriented) and PRG_C, PRG_D (non-healthcare-oriented); all with a €3,200 list price |
| Programme if profile is healthcare | A 55 % · B 35 % · C 5 % · D 5 % |
| Programme if profile is non-healthcare | C 50 % · D 40 % · A 5 % · B 5 % |
| Profile modifier (form) | healthcare 1.05 · non-healthcare 0.95 |

### 3.3 Contact, SLA and ILOC (manual route)

| Parameter | Proposed value |
|---|---|
| Median delay of the first attempt, within working hours (h) | 3 h for all five advisors (lognormal, σ = 1.0) |
| Lead outside working hours | The first attempt is computed from the next working-hours opening |
| Manual leads never touched | 2 % (anomaly) |
| SLA reassignment | If no attempt within 24 calendar hours: reassignment with prob. 0.80; new attempt within ≤ 2 business hours. Zero effect on later conversion |
| Contact probability per step | BD0 call 0.35 · reply to WhatsApp/email 1: 0.08 · BD2 call 0.22 · BD3 email 0.04 · BD4 call 0.22 · WhatsApp 0.06 · BD5 email 0.04 |
| ILOC after no-show | Same probabilities × 0.7 |
| Booking after contact (manual route) | 0.55 |
| Contacted without booking, closing reason | financial 35 % · official_qualification 35 % · future_intake 30 % |

### 3.4 Interviews

| Parameter | Manual route | Bot route |
|---|---|---|
| Scheduling | 1–5 business days after contact, between 09–19 h | 1–4 business days after entry |
| Outcome per appointment: held | 0.65 | 0.55 |
| no_show | 0.22 | 0.30 |
| rescheduled (replacement, not final) | 0.08 | 0.09 |
| cancelled | 0.05 | 0.06 |

| Rule | Proposed value |
|---|---|
| Maximum appointments per lead | 3, counting replacements and new bookings. If the cap is reached, the last appointment's outcome is drawn only from held, no_show and cancelled (renormalised probabilities) |
| After no-show | New booking (`rebooked_after_activity_id`) within ≤ 2 business days with prob. 0.40; otherwise ILOC with BD0 = second business day after the no-show. If the candidate replies during ILOC: new booking with prob. 0.70 |
| After rescheduled | Replacement appointment scheduled 1–5 business days later, linked via `rescheduled_from_activity_id` / `replaced_by_activity_id` |
| After cancelled | New booking (`rebooked_after_activity_id`) with prob. 0.30; otherwise closes with the same mix as "contacted without booking" |
| Bot WhatsApp confirmation (bot route) | Sent in 95 % of cases |
| Automated reminder 24 h before | Sent for 97 % of appointments |
| Personalised advisor WhatsApp | 0 % until 30 June; 60 % of appointments from 1 July. **Zero effect** on show |
| Human pre-interview contact (bot route) | 35 % |

### 3.5 Post-interview and closing

| Transition | Base probability | Timing |
|---|---|---|
| Interview held → form | 0.45 | lognormal, median 2 days, max. 14 |
| Form → link sent | 0.85 | median 2 days, max. 10 |
| Link → enrollment | 0.65 | median 4 days, max. 21 |
| Closure without form | — | 7–21 days after the interview |
| Closure after link without enrollment | — | 10–30 days after the link |

| Rule | Proposed value |
|---|---|
| Bot form reminders | At 24 h and 48 h, if the form has not yet been received |
| Post-interview email sent within ≤ 24 h | 85 % |
| Advisor follow-up within ≤ 48 h of the interview | 80 % |
| `next_step_agreed = true` | 70 %. **Zero effect** on conversion |
| Loss reason: interview without form | financial 40 % · official_qualification 25 % · future_intake 35 % |
| Loss reason: form without link | financial 50 % · future_intake 50 % (no academic rejection is modelled) |
| Loss reason: link without enrollment | financial 60 % · future_intake 40 % |

There is no advisor modifier: all five advisors share the same base parameters (1.00) for response and conversion.

**Post-interview fields** (allowed values):
- `candidate_situation`: employed / unemployed / student / career_change
- `immediate_interest` and `program_interest`: high / medium / low
- `decision_maker`: self / shared / other
- `main_objection`: price / time / official_qualification / timing / none
- `payment_preference`: single / installments / undecided

Field consistency: if the lead is lost for `financial`, `main_objection = price` with prob. 0.70; if lost for `official_qualification`, `main_objection = official_qualification` with prob. 0.70.

### 3.6 Pricing (synthetic rule)

| Parameter | Proposed value |
|---|---|
| Campaign discount | Random draw at each enrollment, independent of date: €600 30 % · €500 40 % · €350 30 %. Arbitrary synthetic scenario |
| Payment-type mix | single 55 % · installments 45 %; if `main_objection = price`: installments 65 % |

| Campaign discount | One-time net | One-time discount | Instalment net |
|---|---|---|---|
| €600 | €2,210.00 | €390.00 | €2,600.00 |
| €500 | €2,295.00 | €405.00 | €2,700.00 |
| €350 | €2,422.50 | €427.50 | €2,850.00 |

Instalment net prices sit above the observed ticket range (€2,000–2,500). This is not corrected artificially; it is documented as a limit of the synthetic rule.

### 3.7 Nurture and reactivation

| Parameter | Proposed value |
|---|---|
| `future_intake` entering nurture | 85 % (`lead_status = nurture`) |
| Nurture emails | 3, roughly every 30 days |
| Emails not sent or failed | 15 % |
| Reactivation | 12 % of people in nurture, 30–150 days later; creates a new lead-deal with `is_reactivation = true` and the same `person_key` |
| Reactivated lead conversion | Same parameters as a manual lead (no extra effect) |

### 3.8 Stalled leads and data-quality anomalies

| Anomaly | Proposed rate |
|---|---|
| Duplicates (rule in §2.4) | Additional 2 % on top of new eligible leads, created 0–14 days after the original |
| Closed-lost without `lost_reason` | 3 % of lost |
| Open leads without an open task | 8 % of open |
| Open leads with an overdue task | 15 % of open |
| Stage change without supporting activity (±24 h) | 4 % of transitions |
| Interviewed leads with ≥1 empty post-interview field | 10 % |
| Stalling (no further activity, lead stays open) | Contacted Opportunity 4 % · Interview Held 5 % · Form Completed 3 %; × 2 in September |

**Deliberate anomalies versus logic errors.** Each anomaly is a deliberate exception to a normal rule and has an allowed scope. Tests detect and report each anomaly (count and rate). A violation outside the allowed scope indicates a generator logic error and fails the test. If the observed rate drifts from the parameter, a warning is raised, not a failure.

| Deliberate anomaly | Normal rule it exempts | Allowed scope | Logic error (test fails) |
|---|---|---|---|
| Closure without `lost_reason` | `closed_lost` ⇒ `lost_reason` not null (R3) | `pipeline_stage = closed_lost` and `lead_status = closed_lost`, closure not produced by ILOC | Null `lost_reason` in nurture, in an ILOC closure, in an open or won lead |
| Manual lead never touched | First human attempt on the manual route | Manual route, open lead with `lead_status = new` | Closed lead without any activity |
| Open without an open task | Every open opportunity has a next task | Open leads | `has_open_task` inconsistent with the tasks in `activities` |
| Overdue task | Tasks completed on time | Open leads | Open overdue task on a closed lead |
| Stage change without supporting activity | Every transition has activity within ±24 h | Any stage timestamp | Stage timestamps out of order (R9) |
| Empty post-interview fields | Fields complete from Interview Held | Leads with a held interview | Post-interview fields filled on a lead without a held interview |
| Stalled lead | Ongoing activity on open leads | Open leads in contacted Opportunity, Interview Held or Form Completed | Closed lead flagged as stalled |
| Duplicate | One row per person and deal | Rows meeting the rule in §2.4 | `is_duplicate` does not match the detection rule |

### 3.9 Implementation notes (v1 generator)

Choices made while implementing §3 that the approved text did not specify. They do not change any approved value.

| Topic | Implementation |
|---|---|
| Simulation method | Each lead's full lifecycle is simulated, then cut at `snapshot_date`: nothing after the cut-off is recorded, and states are derived from events up to it |
| Last arrivals | No lead is created in the 30 minutes before the snapshot, so routing (bot / Opportunity) always happens before the cut-off |
| First-attempt delay | Lognormal in **working hours** (Mon–Fri 09–19) from the next opening; the SLA itself is measured in calendar hours (§2) |
| Reassignment | Checked at the first working moment after 24 calendar hours; the new owner's attempt follows within ≤ 2 working hours |
| Advisor follow-up after the interview | The 80 % parameter is the share *planned* within 48 calendar hours; advisor activity is then moved to working hours, so the realised share within 48 h is lower |
| Stage support records | Each stage change has a dedicated record at the same time (bot booking attempt, booking, appointment time, form received, enrollment link, payment confirmed, closing note). The 4 % omission (§3.8) applies to the omittable ones: opportunity, form_completed and closed_lost |
| Overdue tasks | The 15 % applies to the follow-up task created for open leads without a pending sequence task; stalled leads always carry an overdue task |
| Reactivations | A reactivated lead can enter nurture again but is not reactivated a second time in v1 |
| ILOC and contact | The BD0 call is labelled `first_contact` (or `reschedule` after a no-show) when it connects, and `iloc` when it does not and the sequence starts |
| Ground truth | Injected anomalies are listed in `data/dq_ground_truth.csv`, a validation aid used by the tests; it is not an analytical table |

---

## 4. Interpretation limits

| Limit | Implication |
|---|---|
| 100 % synthetic data | No result describes the real company, team or market |
| Results mirror the parameters | Differences between sources, routes and profiles reproduce the synthetic scenario parameters (§3); the project demonstrates method, it does not discover facts |
| No causality | Zero effect programmed for WhatsApp, training, reassignment and agreed next step. Any observed difference is noise or mix. Estimating effects would require a controlled pilot |
| Workload and advisors | The uneven assignment weight is a scenario parameter, not a real distribution. All five advisors share base parameters, so any difference in workload or conversion comes from chance, the assignment weight and reassignments, and is not attributed to individual performance. Exploratory only |
| Pricing | The synthetic rule does not reconstruct the historical ticket; instalment net prices fall outside the observed range |
| Discount | Random assignment with no time pattern; campaign seasonality cannot be analysed |
| No academic admission | Who approves and eligibility rejections are not modelled |
| No intakes or seats | Group occupancy cannot be estimated |
| No payments or spend | No collections, defaults, CAC or ROI |
| Simplified calendar | No holidays; first response in calendar hours; advisor working hours assumed |
| Reactivation | Technical convention (new lead-deal); it does not describe real CRM behaviour |
| Maturity | Only leads with `snapshot_date − created_at ≥ 60 days` enter cohort conversions; partial and immature cohorts are not compared with mature ones (§2.5) |
