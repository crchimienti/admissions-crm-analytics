**Language:** English | [Español](BASELINE.es.md)

# F0 baseline (`v1.0.0-f0`)

F0 freezes v1 of the project as a verifiable reference before any refactoring (F1). It does not change behaviour: the generator, data, checks and analysis are the v1 ones. All data and figures are synthetic (seed 42).

## What identifies the frozen version

| Item | Meaning |
|---|---|
| `baseline_id` = `v1.0.0-f0` | Human-readable version label, stored in `metrics_v1.json` |
| **Tree id** | SHA-256 of `baseline/MANIFEST.sha256`, which lists the SHA-256 of every repository file (code, config, data, docs, executed notebook, metrics JSON, environment). Any change to any file changes the tree id. The value of each run is printed in `F0_REPORT.md` |
| Git | The folder is not a git repository and no commit was made. When commits are authorised, the same content can be tagged `v1.0.0-f0`; `python scripts/f0_baseline.py --check` then confirms the tagged tree reproduces the manifest |

The tree id is valid for the environment recorded in `environment.txt`. Other library versions may change the executed notebook bytes even with identical data.

## Files

| File | Content |
|---|---|
| `metrics_v1.json` | 47 metrics with definition, unit, population, numerator, denominator, time basis, references to `docs/kpi_definitions*.md`, counts and value; cohort maturity per month; anomaly reconciliation; input hashes; logic-check summary |
| `MANIFEST.sha256` | SHA-256 per file (excludes itself and the run reports) |
| `environment.txt` | Exact Python and library versions used |
| `F0_REPORT.md` · `F0_REPORT.es.md` | Commands executed, exit codes, durations, test results, input hashes, follow-up audit (regenerated on each run) |

Hashes alone do not validate results. The metrics are validated by `tests/test_baseline.py`, which recomputes every metric independently from the CSV files with plain pandas (without importing the notebook's code) and requires equal numerators, denominators and values. It also checks that every metric is fully described, that the README headline figures equal the baseline values in both languages, and that an altered JSON is rejected.

## Source of truth

| Layer | Source of truth | Derived artifact |
|---|---|---|
| Synthetic data | `src/generate_data.py` + `config/simulation_params.yaml` (seed 42) | `data/*.csv` (verified by hash) |
| Integrity rules | `src/checks.py` + `tests/test_integrity.py` | — |
| Metric computation (F0) | Code cells defined in `scripts/build_notebook.py` | `notebooks/admissions_analysis.ipynb` (executed) and `baseline/metrics_v1.json` |
| Metric verification | `tests/test_baseline.py` (independent recomputation) | — |
| Narrative | `scripts/notebook_conclusions.md`, `README*.md`, `docs/` | — |

The executed notebook is a rendered artifact: it is rebuilt from `scripts/build_notebook.py` in a fresh kernel, with run-specific content stripped (execution timestamps, memory addresses, random table ids, split output chunks), so identical inputs give a byte-identical notebook.

**Target for F1 (not done in F0):** move metric computation into a versioned `src/metrics.py`; the notebook would only import and present it, and `metrics_v1.json` would remain the regression reference.

## How to reproduce or verify

```bash
python scripts/f0_baseline.py          # clean run: generate → notebook → tests → manifest → report
python scripts/f0_baseline.py --check  # clean run, then compare with the stored manifest (exit 1 on drift)
```

## Out of scope for F0

No refactoring of the core, no canonical schema, no web app, no CRM connection, no real data.
