**Language:** English | [Español](README.es.md)

# Admissions CRM Analytics — a synthetic B2C admissions case

A portfolio project in **CRM analytics, sales operations and revenue operations**. It models the admissions funnel of a B2C business selling online certificates (lead → contact → admission interview → application form → enrollment link → enrollment), measures it with explicit, tested KPI definitions, and checks that the numbers can be reproduced byte for byte.

> ⚠️ **All data is 100 % synthetic.** The process structure comes from real, anonymised operational experience; every row, rate, amount and result is generated from synthetic scenario parameters (seed 42). Nothing here describes a real company, team, programme, student or market, and no causal claim is made.

## The business problem

An admissions team receives leads through two routes — a bot that books interviews directly and a manual route worked by advisors — and needs to know, with definitions it can defend:

- what share of opportunities reach a **held admission interview** (the main KPI), and how the two routes compare;
- whether leads are contacted fast enough, including those arriving at weekends;
- where the funnel loses people, and whether show rates are measured per appointment or per lead;
- whether the CRM data can be trusted: missing next tasks, overdue follow-ups, closed-lost leads without a reason, stage changes without support records.

## What the project does today

- **Synthetic data with known errors.** A generator produces one year of leads and activities from explicit parameters and injects deliberate data-quality anomalies, listed in a ground-truth file so the detection rules can be tested.
- **Reference metrics engine.** `src/metrics.py` computes **47 metrics**; the notebook only presents them. They are frozen as a baseline with SHA-256 hashes.
- **Canonical CRM contract.** CSV → canonical tables (`crm-canonical/0.1.1`) → admissions adapter, with explicit availability: a KPI whose data is missing is `not_available` with a reason, never a zero.
- **Declarative KPI engine.** **Eight** of those KPIs are also declared in a small YAML configuration and evaluated by a separate engine; the two engines give identical results.
- **Reproducibility.** Frozen references for every phase, more than 400 automated tests, and a one-command full reproduction.

### Scope and current limits

| | |
|---|---|
| Metrics | **47** computed by the reference engine (`src/metrics.py`); only **8** configured in the declarative engine (`src/kpispec`) |
| Data | **100 % synthetic**; real data is out of scope |
| Profile | only the **admissions** profile is tested; no portability to other funnels is claimed |
| CRM | **not connected** to any CRM; no credentials, no API calls |
| Time | the adapter supports synthetic local wall-clock timestamps only; **UTC is not supported yet** |
| Future phases | not implemented: the remaining declarative KPIs, UTC and local-calendar rules, any CRM integration. A local demo exists (`app/`, see below) |

## Main synthetic results

<!-- results:start -->

**Eight KPIs of the declarative engine** (identical to the reference engine)

| KPI | Value | Population (unit) | Time basis |
|---|---|---|---|
| Eligible leads | 7,691 | eligible leads (is_duplicate = false, is_reactivation = false) (lead) | 12 months, all cohorts |
| Share of manual route | 69.9 % | eligible leads (is_duplicate = false, is_reactivation = false) (lead) | 12 months |
| Main KPI: interviews held / opportunities | 45.1 % | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h), both routes (lead) | cohort by created_at month; mature leads only |
| Per-appointment show rate | 69.6 % | eligible appointments: eligible lead, not replaced, scheduled ≤ snapshot (appointment) | period (all appointment months) |
| Forms completed / interviews held | 42.9 % | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h) with a held interview (lead) | cohort by created_at month; mature leads only |
| Manual first attempt ≤ 24 h, weekend arrivals | 36.3 % | eligible manual leads created ≥ 24 h before the snapshot, created Sat–Sun (lead) | period |
| First response, p90 (calendar hours) | 59.7 h | eligible manual leads created ≥ 24 h before the snapshot with an attempt (lead) | period |
| Sales cycle, median (days) | 17.0 days | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h) enrolled (lead) | cohort by created_at month; mature leads only |

**Selected metrics of the reference engine** (12 of 47)

| Metric | Value | Population (unit) | Time basis |
|---|---|---|---|
| Held interview rate, manual route | 31.3 % | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h), entry_path = manual (lead) | cohort by created_at month; mature leads only |
| Held interview rate, bot route | 76.9 % | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h), entry_path = bot_booked (lead) | cohort by created_at month; mature leads only |
| Per-lead show rate | 84.0 % | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h) with ≥1 eligible appointment held or no_show (lead) | cohort by created_at month; mature leads only |
| Enrollments / interviews held | 23.4 % | mature eligible leads (snapshot_date − created_at ≥ 60 × 24 h) with a held interview (lead) | cohort by created_at month; mature leads only |
| Manual first attempt ≤ 24 calendar hours | 69.7 % | eligible manual leads created ≥ 24 h before the snapshot (lead) | period (12 months) |
| Manual first attempt ≤ 24 h, weekday arrivals | 77.4 % | eligible manual leads created ≥ 24 h before the snapshot, created Mon–Fri (lead) | period |
| Manual advisor follow-up within 48 calendar hours | 62.2 % (2,118 / 3,403) | eligible leads whose first held interview + 48 h ≤ snapshot (lead) | period (12 months) |
| Open leads at snapshot | 671 | eligible leads (is_duplicate = false, is_reactivation = false), stage not closed_won/closed_lost (lead) | state at snapshot_date |
| Open leads without next task | 7.2 % | open eligible leads (lead) | state at snapshot_date |
| Average net price (EUR) | €2,522 | enrolled eligible leads (deal) | period |
| Advisor-months above 150 leads (realised / expected before randomness) | 7 / 4 | eligible leads by first_owner_id and created_at month / scenario monthly volume × assignment weight (advisor_month) | period (month) |

Eligible leads 7,691 · mature eligible leads 6,487. Snapshot 2025-12-31 23:59:00. Synthetic data (seed 42). Not real historical results; no causal claims. Population and time-basis definitions are quoted from the reference engine (English). Numerators and denominators of every figure: `python scripts/show_results.py --all`.

<!-- results:end -->

| | | |
|---|---|---|
| ![Funnel of mature cohorts](docs/img/funnel_mature_cohorts.png) | ![Main KPI by cohort](docs/img/main_kpi_by_cohort.png) | ![Show rate by appointment month](docs/img/show_rate_by_month.png) |
| Funnel, mature cohorts | Main KPI by cohort, by route | Per-appointment show rate by month |

What these synthetic results illustrate (method, not facts about the world):

- **Definitions change the answer.** The SLA is measured in calendar hours, so weekend arrivals score far below weekday arrivals in the same scenario; calendar or working hours is a definition to agree before setting a target.
- **Units matter.** Show rate per appointment and per lead answer different questions and are never mixed.
- **The routes differ by construction.** The bot route reaches a held interview much more often than the manual route; the scenario parameters set that gap.
- **Association is not an effect.** After the introduction of the personalised WhatsApp (from 1 July), bot-route cohorts look better than earlier ones, although the generator programs **zero effect** for that intervention; with other seeds the gap disappears.

More detail: [analytical decisions](docs/analytical_decisions.md) and the [executed notebook](notebooks/admissions_analysis.ipynb).

## How to run

You need **Python 3.13** (3.13.16 is the verified version) and about 400 MB of free disk space for the virtual environment. Get the project folder (`git clone https://github.com/crchimienti/admissions-crm-analytics.git`, or unzip a delivered ZIP into a new folder), open a terminal in it, and follow the block for your system. Nothing has to be deleted by hand: the scripts clean up after themselves.

**macOS / Linux**

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python scripts/show_results.py              # quick start (< 1 min); add --lang es for Spanish
python -m pytest -q                         # tests (about 4–10 min)
python scripts/release_run.py --mode portable   # analytical reproduction (about 10 min), see below
python scripts/release_run.py --check           # strict reproduction, PNG images included (Linux reference)
```

**Windows (PowerShell)**

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1                  # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned
python -m pip install -r requirements-lock.txt
python scripts\show_results.py              # quick start (< 1 min); add --lang es for Spanish
python -m pytest -q                         # tests (about 4–10 min)
python scripts\release_run.py --mode portable   # analytical reproduction (about 10 min), see below
```

- **Quick start** — `show_results.py` computes the eight declarative KPIs and the 47 reference metrics in memory from `data/`, checks them against the frozen baseline and prints them with their population, unit and time basis. It writes no file and never runs the generator.
- **Notebook** — `notebooks/admissions_analysis.ipynb` is versioned already executed, so it can be read on GitHub or in any notebook viewer. Opening it interactively needs JupyterLab, which is optional and not part of `requirements-lock.txt`; it is not needed to run or verify the project.
- **Tests** — integrity, baseline, regression, contract, engine, serialization, release and verification-mode checks.
- **Reproduction, two separate levels.** Both regenerate the data and the notebook, run every test and compare with the frozen references; the chart fonts ship with the project (`assets/fonts/inter/`, SIL Open Font License 1.1) and nothing has to be installed or configured.
  - **Portable analytical** (`--mode portable`): data bytes, the 47 metrics and the 8 KPIs, every notebook cell, text, table and number (identical to F1, with no exempted field), execution without errors, and the structure of every chart — data, titles, labels, legends — checked exactly by `scripts/chart_signature.py`. If the PNG images differ, it says so in a separate section of its report (`build/portable/PORTABLE_REPORT.md`, outside the versioned files) and keeps the versioned notebook and figures. It is **not** a byte-for-byte reproduction of the notebook.
  - **Strict graphical** (default, `--check`): everything above, plus the notebook byte-identical to F1 **including its PNG images**. It fails if any image differs. Verified on the Linux reference environment only.

**What is reproduced, and where it has been checked.**

| Level | Check | Linux | Windows | macOS |
|---|---|---|---|---|
| Figures | the 47 reference metrics and the 8 declarative KPIs equal the frozen references | tested | verified by the project owner on Windows 11 AMD64 with v1.4.3-gh (2026-10-15): 8/8 KPIs, 477 tests passed | pending |
| Data files | the three generated CSV files are byte-identical to F0 | tested | verified by the project owner on Windows 11 AMD64 with v1.4.3-gh (2026-10-15) (portable reproduction) | pending |
| Notebook analysis | every cell, text, table and number identical to F1; execution without errors; chart structure | tested | verified by the project owner on Windows 11 AMD64 with v1.4.3-gh (2026-10-15): portable analytical verification passed, chart structure of the 5 charts identical | pending |
| Chart rendering | notebook byte-identical to F1, including the 5 PNG images | tested, with no system font and no external configuration | **not passed**: the 5 PNG images differ from the Linux reference; cause not determined; accepted as a limitation of strict rendering across platforms | pending |

**Local demo (Streamlit, optional).** A small local app to explore the results: summary of the eight KPIs, funnel and the notebook charts, the 47 reference metrics, and definitions and limits, in Spanish or English. It only reads what the project already computes (no new formula), runs on `localhost`, sends no usage statistics, accepts no uploads and never runs the generator or the tests. It has **no interactive filters**: the current functions compute each metric on its whole population, and filtering would need a new route for populations and denominators. Use a separate virtual environment, so the pinned analytical one is not changed:

```powershell
py -3.13 -m venv venv                       # macOS / Linux: python3.13 -m venv venv
venv\Scripts\Activate.ps1                   # macOS / Linux: source venv/bin/activate
python -m pip install -r requirements-app.txt
python -m streamlit run app/streamlit_app.py   # opens http://localhost:8501 — stop with Ctrl+C
```

`requirements-app.txt` is `requirements-lock.txt` plus Streamlit 1.65.0 and its dependencies, all pinned. Tested on Linux (automated tests, server start, review in a headless browser). Windows: start-up and initial visual review on Windows confirmed by the user (v1.5.0-app, 2026-10-15); the test suite has not been run on Windows with this version. macOS: pending.

**Environment files.** `requirements-lock.txt` pins every package; its eight reference packages are exactly the versions recorded in [`baseline/environment.txt`](baseline/environment.txt), and platform-only dependencies carry environment markers. `requirements.txt` (minimum versions, unchanged since v1) is kept for reference but does not pin versions, so it can install newer releases than the ones verified.

**Platform status.**

| System | Status |
|---|---|
| Linux x86-64, Python 3.13.16 | **tested**: clean virtual environment from the lock file, quick start, all tests, strict and portable reproductions without any external chart configuration |
| Windows 11 AMD64 | **portable analytical level verified by the project owner** with v1.4.3-gh (2026-10-15, PowerShell, Python 3.13.16, pinned environment identical to `baseline/environment.txt`): 477 tests passed (0 failed, xfail or xpass), 8/8 KPIs, the 5 chart signatures identical, every command of the portable report with exit code 0, versioned notebook and figures not overwritten. **Strict graphical level not passed**: the PNG images differ; cause not determined; accepted as a limitation. Not run by the maintainer of this delivery on Windows |
| macOS (Apple Silicon, Intel ≥ 10.15) | **prepared, not yet verified**: a wheel exists for every pinned package; the workflow will run the tests and the portable reproduction there |

## Repository map

| Folder | Content |
|---|---|
| [`src/`](src) | generator, integrity checks, reference engine (`metrics.py`), canonical contract (`canonical/`), declarative engine (`kpispec/`) |
| [`profiles/admissions/`](profiles/admissions) | CSV mapping, profile rules, KPI requirements, the eight declarative KPIs (`kpis.yaml`) |
| [`schema/`](schema) | canonical contract `crm-canonical/0.1.1` and KPI language `kpi-spec/0.1` |
| [`data/`](data) | the three synthetic CSV files (generated, versioned because the tests and the quick start use them) |
| [`notebooks/`](notebooks) | the executed analysis notebook |
| [`docs/`](docs) | assumptions, data dictionary, KPI definitions, contract and KPI specification, analytical decisions, project status |
| [`assets/fonts/inter/`](assets/fonts/inter) | the two Inter font files that draw the notebook charts, with their licence and provenance |
| [`app/`](app) | the local Streamlit demo (`streamlit_app.py`) and its data layer (`app_data.py`), which only reads existing results |
| [`scripts/`](scripts) | quick start, figure export, full reproduction; the tools of earlier phases refuse to run on this tree |
| [`tests/`](tests) | all automated tests and the hand-calculated fixtures |
| [`baseline/`](baseline), [`reports/`](reports) | frozen references of each phase and the release report |

## History and verification

The project was built in approved phases, each frozen with SHA-256 manifests: F0 baseline (`v1.0.0-f0`), F1 single metrics module (`v1.1.0-f1`), F2 canonical contract (`v1.2.3-f2`), F3.0 declarative KPIs (`v1.3.1-f3`) and this GitHub preparation (`v1.4.0-gh`).

- [CHANGELOG](CHANGELOG.md) — one line per version, with its tree id.
- [Project status](docs/PROJECT_STATUS.md) — decisions, frozen versions and open items.
- [Release report](reports/release/RELEASE_REPORT.md) — what the full reproduction checked on the last run.
- [Declarative KPI specification](docs/kpi_spec.md) · [canonical contract](docs/canonical_schema.md) · [KPI definitions](docs/kpi_definitions.md) · [assumptions and limits](docs/assumptions.md).

## Privacy and licence

No real CRM exports, names, emails, phone numbers or identifiers were used or requested. Companies, brands and programmes are not named; programmes are aliases (`PRG_A`–`PRG_D`) and advisors are `ADV_01`–`ADV_05`.

**Licences** — Copyright (c) 2026 Carlos Eduardo Rodriguez Chimienti.

| Part | Licence |
|---|---|
| Source code and configuration (`src/`, `scripts/`, `tests/` code, `app/`, `schema/`, `profiles/`, `config/`, `.github/`, `.streamlit/`) and the **code cells** of the notebook | MIT — [`LICENSE`](LICENSE) |
| Documentation, original charts (`docs/img/`, notebook images), synthetic data (`data/`, test fixtures), reports, and the **narrative cells, charts and outputs** of the notebook | CC BY 4.0 — [`LICENSE-CONTENT`](LICENSE-CONTENT), to the extent rights exist in them |
| Inter font files (`assets/fonts/inter/`) | SIL Open Font License 1.1, by The Inter Project Authors — [`OFL.txt`](assets/fonts/inter/OFL.txt), unchanged |

Third-party material keeps its own licences and notices. No exclusive rights are claimed over material not protected by copyright (for example individual synthetic values or parts produced with AI assistance where no rights exist). Suggested attribution for the content: *Carlos Eduardo Rodriguez Chimienti — Admissions CRM Analytics* (https://github.com/crchimienti/admissions-crm-analytics/), CC BY 4.0; details in [`LICENSE-CONTENT`](LICENSE-CONTENT).
