**Language:** English | [Español](PROJECT_STATUS.es.md)

# Project status (GitHub preparation, `v1.4.4-gh`)

> **Use:** this document is the reference when a session is resumed. If a specification is not found here or in the files it cites, **it is not substituted or reconstructed**: it is requested from the project owner. Any change to this document must reflect an approved decision.

## 1. Restrictions and goals

### 1.1 Project principles (no expiry)

- No company, brand, programme, student, advisor or client is named or identified.
- Synthetic results are never presented as real historical results. No causal claim is made from simulated data.
- Bilingual EN/ES documentation. Anonymised real context, analytical decisions, synthetic parameters and synthetic results are kept separate.
- Each phase is implemented only after explicit approval, and stops when finished.

### 1.2 Current restrictions, until further authorisation

These are not permanent prohibitions: they apply until the project owner explicitly authorises otherwise for a given phase.

- Synthetic data only, created from scratch. No real data, exports, screenshots, names, emails, phone numbers or identifiers are used or requested.
- No HubSpot or other CRM connection.
- No web app (Streamlit or other).
- No Git repository, commits, tags or publication on GitHub. The GitHub preparation (`v1.4.0-gh`) is local only.
- The synthetic generator is not generalised yet, and no portability to other funnels is claimed.

### 1.3 Future goals (not authorised yet)

They are part of the project's planned evolution, but none is authorised or started. Each needs its own plan and approval:

- A web-app MVP working on CSV files and synthetic data, with no credentials and no real CRM.
- A read-only HubSpot integration, as a separate phase.
- Publication of the repository on GitHub.
- A test with a second, generic funnel before any portability claim.

## 2. Frozen versions

| Version | Content | Identifier | Where |
|---|---|---|---|
| `v1.0.0-f0` | F0 baseline (47 metrics) | tree id `eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df` (SHA-256 of `baseline/MANIFEST.sha256`) | `baseline/`, `admissions-crm-analytics-v1.0.0-f0.zip` |
| `v1.1.0-f1` | `src/metrics.py` as single source | tree id `9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651` | `reports/f1/`, `admissions-crm-analytics-v1.1.0-f1.zip` |
| `v1.2.0-f2` | canonical contract, mapping, adapter, fixture | tree id `2ba1a33f9001b613ed75192eee11c6c7c591c3cb321e51c07cb995b375eddc1e` | `reports/f2/MANIFEST_F2_v1.2.0.sha256`, ZIP v1.2.0-f2 |
| `v1.2.1-f2` | `metrics.py` robustness fix, official fixture | tree id `f71ca2471525fbaa28b3b2a29f1012f5c9a18671a2f57c178de97a15788a95e4` | `reports/f2/MANIFEST_F2_v1.2.1.sha256`, ZIP v1.2.1-f2 |
| `v1.2.2-f2` | contract 0.1.1 (`seq`), event order, contract documentation — approved as the F2 working version | tree id `ddfc93cf87313a3b22d4a59961d938c420fcd97d15c8b530b0947457d9afc1a9` | `reports/f2/MANIFEST_F2_v1.2.2.sha256`, ZIP v1.2.2-f2 |
| `v1.2.3-f2` | documentation-only correction of v1.2.2-f2 — **F2 close, frozen** | tree id `a1df9fca9a38538f912fadfb437b4831f609962baa7b97fe763f68ec7a0885db` | `reports/f2/`, ZIP v1.2.3-f2 |
| `v1.3.0-f3` | F3.0: declarative specification of 8 KPIs and an engine in parallel with `metrics.py` | tree id `b189d44e9d092d3481817a28e7fcca98535cf311286affa079bf5af1d560e1bd` | `reports/f3/MANIFEST_F3_v1.3.0.sha256`, ZIP v1.3.0-f3 |
| `v1.3.1-f3` | F3.0 corrections against the approval spec: the engine no longer loads `metrics.py` even indirectly, HF for stage fields, APT+FLD combined, eligibility equivalence on all five variants, tests and F3.5 text — **F3.0 close, frozen** (approved on 2026-10-14) | tree id `f1a73209cfaf24d3768784e121f376e1d0ec485eca31ddd22f2b57e09ef23c34` | `reports/f3/`, ZIP v1.3.1-f3 |
| `v1.4.0-gh` | GitHub preparation (local only): visitor README, pinned environment, line-ending fix, quick start, figures, analytical decisions, release run, CI workflow (not run) | tree id `e1c13bfa5390ed5128970700941e63887ed999f6304cc1b96e946b0479b4a41d` | `reports/release/MANIFEST_RELEASE_v1.4.0.sha256`, ZIP v1.4.0-gh |
| `v1.4.1-gh` | bounded revision of v1.4.0-gh (local only): reference chart rendering fixed by the project (bundled Inter fonts, OFL 1.1), Windows path comparison in `test_reports_f2_frozen`, README results block and wording | tree id `a2e68371cadd318a0d2d72d33d55663ab68d41dea2d7706253cbcbb927d9c7bb` | `reports/release/MANIFEST_RELEASE_v1.4.1.sha256`, ZIP v1.4.1-gh |
| `v1.4.2-gh` | authorised compatibility fix found on Windows: the temporary CSV of `test_regeneration_is_reproducible` is written with LF | tree id `98841cc859eec50fb11a2772263dbc1595f16ce4a86952584729791e1c8096c2` | `reports/release/MANIFEST_RELEASE_v1.4.2.sha256`, ZIP v1.4.2-gh |
| `v1.4.3-gh` | verification levels separated: portable analytical (`--mode portable`) and strict graphical (default); chart structure signature; separate CI jobs | tree id `a9da920c3e2e8a3b7ee6fed8fff5875faf25fd2b05ebe840c859e3841c232d7b` | `reports/release/MANIFEST_RELEASE_v1.4.3.sha256`, ZIP v1.4.3-gh |
| `v1.4.4-gh` | licences (MIT for code, CC BY 4.0 for content, Inter fonts under SIL OFL 1.1) and documentation of the Windows result; no change to code, data, notebook, charts or fonts — final local version before the first commit | tree id = SHA-256 of `reports/release/MANIFEST_RELEASE.sha256` (shown in `reports/release/RELEASE_REPORT.md`) | `reports/release/`, ZIP v1.4.4-gh |

`baseline/`, `reports/f1/`, `reports/f2/` and `reports/f3/` are never written. `scripts/f0_baseline.py`, `scripts/f1_run.py`, `scripts/export_metrics.py`, `scripts/f2_run.py` and `scripts/f3_run.py` refuse to run on the current tree. F0, F1, F2 and F3 are verified from their ZIPs in a clean folder. The current tree is verified with `python scripts/release_run.py --check`, which compares it with `reports/f3/MANIFEST_F3.sha256` read-only and writes only `reports/release/`.

## 3. Authorised modifications of files from frozen phases

- `src/metrics.py` (F1): v1.2.1-f2 robustness fix (zero denominators, empty appointment structures). No definition and none of the 47 values changed. Its hash is pinned in `tests/test_regression_f1.py`.
- `scripts/f1_run.py` and `scripts/export_metrics.py`: only the guard that prevents writing to `reports/f1/`.
- `README.md` and `README.es.md`: F2 and F3.0 sections, with no figure changed.
- `scripts/f2_run.py` (F2): only the F3.0 guard that prevents rewriting `reports/f2/`.
- `src/canonical/adapters/admissions.py` (F2): in F3.0, `first_human_attempt` is extracted as a reusable profile function, with the same results.
- **v1.4.0-gh** (approved on 2026-10-14):
  - `src/generate_data.py` (F0) and `scripts/build_notebook.py` (F1): line-ending fix only (`lineterminator="\n"` in the three CSV writes; the notebook is written through a file opened with `newline="\n"`). The bytes produced on Linux are unchanged; with a simulated Windows line separator the CSV bytes now equal F0.
  - `.gitignore`: rules for virtual environments, secrets, local copies, editors and `build/`; the original four rules are kept.
  - `scripts/f3_run.py` (F3): only the guard that prevents rewriting `reports/f3/`.
  - `tests/test_regression_f0.py`, `test_regression_f1.py`, `test_regression_f2.py`: they recognise these changes; code files are pinned to their new hashes (`tests/release_declared.py`).
  - `README(.es).md` rewritten for visitors; `docs/PROJECT_STATUS(.es).md` updated.
- **v1.4.1-gh** (approved on 2026-10-14, bounded revision):
  - `scripts/build_notebook.py` (F1): the reference chart rendering is applied in the kernel before the first cell through `scripts/notebook_rendering.py` and the fonts in `assets/fonts/inter/`; the notebook cells are unchanged and the rebuilt notebook equals F1 byte for byte on Linux. New hash pinned in `tests/release_declared.py`.
  - `tests/test_regression_f2.py`: `test_reports_f2_frozen` compares relative POSIX paths (same pinned hashes); focused separator test added.
  - The v1.4.0-gh manifest is kept as `reports/release/MANIFEST_RELEASE_v1.4.0.sha256` and compared read-only.
  - Rendering details: matplotlib's built-in defaults are applied first (no user or site `matplotlibrc` is read); if the kernel cannot apply the rendering, the build stops with an explicit message. `assets/fonts/inter/OFL.txt` is the upstream Inter v4.0 licence file, unchanged. The workflow's manual reproduction job runs on Linux, Windows and macOS.
- **v1.4.2-gh** (approved on 2026-10-14, authorised compatibility fix): `tests/test_integrity.py` (F0) — in `test_regeneration_is_reproducible` the temporary CSV is written with `lineterminator="\n"`, as the generator does; the byte-for-byte comparison with `data/` is unchanged and nothing is excluded on Windows. Found by the project owner on Windows with v1.4.1-gh (451 passed, 1 failed). The new hash is pinned in `tests/release_declared.py`, so only this change is recognised; `tests/test_serialization.py` now checks every `to_csv` call in the tests. No other temporary write of the tests had the same problem (the others write bytes, or already set the line ending).
- **v1.4.3-gh** (approved on 2026-10-14, validation correction only): two verification levels, always reported separately. **Portable analytical** (`python scripts/release_run.py --mode portable`): CSV bytes = F0; the 47 metrics and 8 KPIs; every notebook cell, text, table, number, execution count and metadata identical to F1, with no exempted volatile field (only the PNG payloads may differ); execution without errors; chart structure (data, titles, axis labels, legends, annotations) identical to `tests/chart_signature_reference.json`, computed by `scripts/chart_signature.py` independently of pixel rendering and compared exactly (no visual tolerance); tests, documents, frozen references and the stored manifest. PNG differences go to a separate section with both notebook hashes, image sizes and the rendering environments; the portable report is written to `build/portable/` (ignored by Git, outside every reference manifest); the versioned notebook and figures are restored and never overwritten; `reports/release/` is never written. **Strict graphical** (default, `--check`): the notebook must also be byte-identical to F1, PNG images included; it fails otherwise. F1 and every reference are unchanged. CI: `reproduction-portable` (Linux, Windows, macOS) and `reproduction-strict` (Linux) are separate jobs.
- **v1.4.4-gh** (approved on 2026-10-15, licences and documentation only):
  - Licences decided by the project owner: holder **Carlos Eduardo Rodriguez Chimienti**, year 2026. MIT for the original source code and configuration, including the notebook code cells (`LICENSE`, official MIT text). CC BY 4.0 for documentation, original charts, synthetic data, reports and the notebook narrative cells, charts and outputs, to the extent rights exist (`LICENSE-CONTENT`, with scope and attribution). Inter fonts and all third-party material keep their own licences and notices (`assets/fonts/inter/OFL.txt` unchanged). No exclusive rights are claimed over unprotected material. Suggested attribution: *Carlos Eduardo Rodriguez Chimienti — Admissions CRM Analytics*; the repository URL will be added once it exists.
  - Decisions of 2026-10-15: the PNG difference between Windows and Linux is accepted as a limitation of strict rendering across platforms; no further changes of fonts, hinting, rendering or references to force it; Windows is described as verified for the portable analytical scope only; macOS stays unverified; JupyterLab (interactive viewing) is optional, not installed in the owner's environment, and not a failure of the notebook execution — no package is added for it.

## 4. Current contract: `crm-canonical/0.1.1`

- File: `schema/canonical_v0.1.1.yaml`. `schema/canonical_v0.1.yaml` is kept unchanged. 0.1 datasets remain valid; only 0.1.1 datasets may carry `stage_events.seq`.
- Tables: `dataset`, `records`, `stage_events` (optional), `activities`, `appointments` (optional, capability) and `record_attributes` (`adm_` prefix).
- `history_mode`: `full_event_history`, `milestone_first_entry` or `snapshot_only`. History is never inferred from `current_stage`, appointments or activities.
- Timestamps: `naive_wall_clock` only for synthetic or legacy data (Europe/Madrid as metadata). `utc` otherwise, with an error on ambiguous or non-existent local times. The admissions adapter accepts only `naive_wall_clock` in F2.
- Event order: `seq` if the source provides it; otherwise `occurred_at`. With ties and no `seq` the order is indeterminate and is not invented. Only `time_in_stage` depends on order, and it is then reported as `ORD`.
- Differences from the approved plan (`is_duplicate` → `record_origin`, `status` → `current_status` + outcome derived from `current_stage`, `closed_at` → `won_at`/`lost_at`, `stage_events` correspondence, `exited_at` and `changed_by_type` not represented): `docs/canonical_schema.md` §11.
- Approved `stage_events` specification (provided by the project owner on 2026-10-13): key (`record_id`, `seq`); required `record_id`, `seq`, `stage`, `entered_at`, `event_kind`; optional `exited_at`, `changed_by_type`; `seq` orders ties.
- Neutral rules C01–C09 (contract); profile rules P01–P10 (`profiles/admissions/rules.yaml`). The reactivation-parent rule belongs to the profile, not to the contract.

## 5. KPI availability

- Catalogue of 31 indicators: 24 metrics and 7 history indicators. `time_in_stage` is a capability with no expected value in the fixture.
- Reasons for not being available:
  - module absent: `HM` (no milestones), `HF` (no full history), `AUT` (no `is_automated`), `APT` (no appointments);
  - computed: `DEN0` (zero denominator), `INSUF` (no observations), `ORD` (indeterminate order);
  - field not provided: `FLD` (approved in F3.0): a required field or attribute is not provided by the load or the profile; `missing` lists the exact fields. It combines with the others (e.g. `FLD+AUT`).
- A `not_available` KPI carries only `id`, `status`, `reason` and `missing`; never a value, numerator or denominator. A true zero stays an available 0.
- Fixture matrix (available + not available): `v_full` 31+0, `v_milestone` 25+6, `v_snapshot` 16+15, `v_no_automated` 23+8, `v_no_appointments` 25+6. The generated admissions dataset behaves like `v_milestone`.

## 6. Official fixtures

- `tests/fixtures/canonical_handcalc/`: **12 hand-built records**, snapshot **2025-07-31 23:59:00**, five variants. `expected.json` holds the source tables, derivations, every expected value, the coverage inventory and the provenance.
  - Values accepted on 2026-10-13 include: `contact_rate` = 7/8, `followup_48h_manual_advisor` = 3/4, regressions 1/25, reopens 1/4.
  - It replaces the earlier 9-record draft (R1–R9, snapshot 2025-03-31), which is **not recoverable and must not be reconstructed**.
  - No return to the old fixture, and no change of the snapshot to June.
- `tests/fixtures/mapping_errors/`: a valid CSV pair and 21 error cases.
- `tests/fixtures/timezones/`: daylight-saving cases in Europe/Madrid.

## 7. Approved decisions by phase (summary)

- **v1:** four independent dimensions (`pipeline_stage`, `interview_outcome`, `lead_status`, `lost_reason`); a no-show stays in Interview Booked.
  - Main KPI: mature eligible leads with at least one held interview / all mature eligible leads, both routes.
  - Maturity: 60 × 24 h per lead.
  - ILOC in business days; SLA and follow-up in calendar hours; manual follow-up in (held, held + 48 h].
  - Anomalies reconciled in the same unit as the ground truth.
- **F0:** frozen baseline of 47 metrics, with SHA-256 hashes.
- **F1:** `src/metrics.py` as single source; the notebook only presents results; 47/47 equal to F0.
- **F2:** canonical contract, CSV → canonical mapping, adapter to the `metrics.py` `Context`, and explicit availability; architecture CSV → canonical → `adapters/admissions` → `metrics.py`.
  - v1.2.1: authorised robustness fix; the 12-record fixture becomes official.
  - v1.2.2: optional `seq` and event order.
- **F3.0 (approved on 2026-10-13):** declarative specification `kpi-spec/0.1` (`schema/kpi_spec_v0.1.yaml`, `profiles/admissions/kpis.yaml`, `docs/kpi_spec.md`).
  - Engine in parallel: `src/metrics.py` stays the official reference and is not modified.
  - Eight KPIs only: `eligible_leads`, `share_manual_route`, `main_kpi_interviews_held_over_opportunities`, `show_rate_per_appointment`, `forms_over_interviews_held`, `sla_first_attempt_24h_manual_weekend`, `first_response_p90_hours`, `sales_cycle_median_days`.
  - Closed language: five operations (`count`, `share`, `ratio`, `duration_stat`, `field_stat`), AND-only filters, no expressions, no OR, no code.
  - No field assumed available; `FLD` reason.
  - Ratios with the same unit and a mandatory `relation` (`subset_of`, `same_base`, `independent_allowed`).
  - Eligibility: `record_origin = original` ⇔ `is_duplicate = false` and `is_reactivation = false` is an admissions profile rule, tested on the generated data, the canonical path (CSV → canonical → adapter), the 12-record fixture and all five fixture variants; an unknown, null or absent origin never enters `eligible` silently.

- **GitHub preparation `v1.4.0-gh` (approved on 2026-10-14):**
  - Versioned: the three synthetic CSV files, the fixtures, the executed notebook and every reference, report and manifest the tests need. Not versioned: local ZIP copies, diffs, caches, virtual environments, secrets, `build/`.
  - `.gitattributes` with `* -text`: no end-of-line conversion, so a checkout on any system gets the committed bytes.
  - `requirements-lock.txt` pins the full environment (its eight reference packages equal `baseline/environment.txt`; platform-only dependencies with markers); `requirements.txt` is unchanged. App dependencies stay separate and are not added yet.
  - `scripts/show_results.py` is read-only; `scripts/export_figures.py` extracts three figures from the executed notebook without recomputing; `scripts/release_run.py` is the full reproduction for the current tree.
  - Identifiers: `v1.4.0-gh` for this preparation; `v1.5.0-app` reserved for the local demo. Earlier identifiers are kept; no retroactive commits or tags.
  - Filters that recompute KPIs are out of the first demo; no new analytical routes in this preparation.
  - Windows and macOS are "prepared, not yet verified" until the CI workflow has run there.

## 8. Open items

- **F2 closed and frozen** at `v1.2.3-f2`.
- **F3.0 closed and frozen** at `v1.3.1-f3` (approved on 2026-10-14).
- **`v1.4.4-gh` delivered** (licences and documentation over `v1.4.3-gh`), pending review by the project owner before the first commit.
  - **Licence — decided on 2026-10-15** (see §3, v1.4.4-gh): `LICENSE` (MIT) and `LICENSE-CONTENT` (CC BY 4.0).
  - **Chart rendering of the notebook — resolved in v1.4.1-gh on Linux.** `scripts/build_notebook.py` applies the reference rendering inside the kernel before the first cell (`scripts/notebook_rendering.py`): the two Inter 4.000 files shipped in `assets/fonts/inter/` (SIL OFL 1.1, hashes and provenance in `FONTS.md`), `font.family = Inter, sans-serif, DejaVu Sans`, `text.hinting = no_hinting`; any other font named Inter is ignored and a missing or changed file stops the build. Verified on Linux with no system Inter font and no external configuration: the rebuilt notebook equals F1 byte for byte. Windows: the PNG images differ (accepted limitation, see below); macOS: not verified.
  - **Windows path comparison — corrected in v1.4.1-gh.** `test_reports_f2_frozen` compares relative POSIX paths, as written in the manifests (same pinned hashes); a focused test covers Windows and POSIX separators with pure paths. It does not replace running the suite on Windows.
  - **Windows 11 AMD64 — portable analytical verification passed** (run by the project owner with v1.4.3-gh on 2026-10-15 at 08:32, PowerShell, Python 3.13.16, pinned environment identical to `baseline/environment.txt`): 477 tests passed (0 failed, xfail or xpass); 8/8 declarative KPIs; the 5 chart signatures identical to the reference (data, titles, labels, legends); every command of the portable report with exit code 0; versioned notebook and figures not overwritten. Rendering environment reported: matplotlib 3.11.2, FreeType 2.14.3 (local build), numpy 2.5.3, Pillow 12.3.0, project Inter fonts with the recorded hashes — the same versions as the Linux reference. **Strict graphical verification not passed**: the PNG images differ; the cause is not determined and is not attributed to any library; accepted as a limitation. Earlier (v1.4.2-gh): installation, quick start, CSV regeneration and 453 tests verified. v1.4.4-gh has not been run on Windows.
  - **Linux:** analytical and strict graphical levels tested by the maintainer of the deliveries (unchanged).
  - **macOS:** not verified.
  - **JupyterLab:** optional interactive viewing; not part of the pinned environment.
  - **Next step (by the project owner, when authorised):** create the repository, make one first commit of `v1.4.4-gh` and tag it; no retroactive commits or tags; then add the repository URL to the attribution.
- **Local demo `v1.5.0-app` planned, not authorised.** Requirements recorded for its plan:
  - no external connections, CRM or telemetry; local browser–server communication only;
  - caches may exist, but data, code and versioned references must stay intact;
  - only functions and views that exist and are tested; no mature-cohort filter promised as an existing parameter without checking its API;
  - the generator and the tests are never run when the app opens or on interaction;
  - no upload of arbitrary CSV files, no YAML editing, no public deployment.
- **F3.1 not authorised:** the remaining 27 parametrisable KPIs, with no new operations.
- **F3.5 decided, not yet authorised** (UTC support and local-calendar rules): a small, independent phase after F3.0 and before any F4, real data or CRM connector. Its design is recorded here, and it needs its own explicit approval. It will:
  - store and compute durations on UTC instants;
  - evaluate weekday, `same_calendar_date`, working hours and calendar rules in `source_timezone`;
  - include daylight-saving (DST) fixtures;
  - demonstrate that a 24-hour duration and a local calendar day are not always equivalent;
  - keep the regression against the synthetic `naive_wall_clock` case.

  F3.0 contains no UTC code.
- **F4 not defined or started.** It needs a plan and explicit approval.
- **Future goals not authorised:** see §1.3.
- **`stage_events` specification columns not implemented** (`exited_at`, `changed_by_type`): they would be added only with approval and a new contract version.
- **Adapter with `timestamp_mode = utc`: not supported.** The contract and the mapping accept and validate UTC timestamps, but the admissions adapter rejects such datasets (`A_TIMESTAMP_MODE`).
- **No readiness for real data and no working CRM connection.** Everything tested uses synthetic data and local CSV files. There is no connector, credential or CRM read flow, and the project has not been tested on real data.
