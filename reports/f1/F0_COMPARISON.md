**Language:** English | [Español](F0_COMPARISON.es.md)

# F1 vs F0 — file and metric comparison

Reference: `v1.0.0-f0` (`baseline/MANIFEST.sha256`, tree id `eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df`). Hashes shown truncated to 16 characters.

## Files

| File | Status | SHA-256 F0 | SHA-256 F1 | Declared change |
|---|---|---|---|---|
| `.gitignore` | unchanged | `b9e0ad01d09ecce2` | `b9e0ad01d09ecce2` |  |
| `README.es.md` | modified (declared) | `81084ef94c5999cd` | `925c03b7bc25faf6` | estructura, cómo ejecutar, fuente de verdad (ninguna cifra cambia) |
| `README.md` | modified (declared) | `46e157c2c9a1ff66` | `d506000a42669b5d` | repository structure, how to run, source of truth (no figure changed) |
| `baseline/BASELINE.es.md` | unchanged | `aeffc4b4b5e6ee54` | `aeffc4b4b5e6ee54` |  |
| `baseline/BASELINE.md` | unchanged | `fda359fc410c99ac` | `fda359fc410c99ac` |  |
| `baseline/F0_REPORT.es.md` | unchanged | `418a2a5a2cd59e03` | `418a2a5a2cd59e03` |  |
| `baseline/F0_REPORT.md` | unchanged | `573dc315e20b5cbb` | `573dc315e20b5cbb` |  |
| `baseline/MANIFEST.sha256` | unchanged | `eb4f60681f71e88a` | `eb4f60681f71e88a` |  |
| `baseline/environment.txt` | unchanged | `d1b68e06d86d6736` | `d1b68e06d86d6736` |  |
| `baseline/metrics_v1.json` | unchanged | `921af3e18cce2613` | `921af3e18cce2613` |  |
| `config/simulation_params.yaml` | unchanged | `51c5d18fb1c7b322` | `51c5d18fb1c7b322` |  |
| `data/activities.csv` | unchanged | `3318a0b81877ae8b` | `3318a0b81877ae8b` |  |
| `data/dq_ground_truth.csv` | unchanged | `f0dc4ac66ddc789d` | `f0dc4ac66ddc789d` |  |
| `data/leads.csv` | unchanged | `255720913fea99f2` | `255720913fea99f2` |  |
| `docs/assumptions.es.md` | unchanged | `43040e6e83651a3b` | `43040e6e83651a3b` |  |
| `docs/assumptions.md` | unchanged | `cd7953a731187b4a` | `cd7953a731187b4a` |  |
| `docs/data_dictionary.es.md` | unchanged | `f4660bdf0e77b500` | `f4660bdf0e77b500` |  |
| `docs/data_dictionary.md` | unchanged | `6095fc6c5eb1ba45` | `6095fc6c5eb1ba45` |  |
| `docs/kpi_definitions.es.md` | unchanged | `9b744adda9dc09f8` | `9b744adda9dc09f8` |  |
| `docs/kpi_definitions.md` | unchanged | `2c20dafad010a445` | `2c20dafad010a445` |  |
| `notebooks/admissions_analysis.ipynb` | modified (declared) | `26bf7e088de7c5b7` | `d40074d45d635b18` | rebuilt from the new cells (same values; different code and layout) |
| `reports/f1/metrics_f1.json` | new (declared) | `—` | `4538857acc710a84` |  |
| `requirements.txt` | unchanged | `fea7aa31645369df` | `fea7aa31645369df` |  |
| `scripts/build_notebook.py` | modified (declared) | `263ad1008549984d` | `579d547a100d7db9` | notebook cells now call src/metrics.py; no longer writes baseline/ |
| `scripts/export_metrics.py` | new (declared) | `—` | `e30b3427b759278d` |  |
| `scripts/f0_baseline.py` | modified (declared) | `f1c0ceb72375387e` | `61b821c085e31b16` | guard only: refuses to run on the F1 tree |
| `scripts/f1_run.py` | new (declared) | `—` | `352fd74878b4dea8` |  |
| `scripts/notebook_conclusions.md` | unchanged | `d2f5c04e765b4380` | `d2f5c04e765b4380` |  |
| `src/calendar_utils.py` | unchanged | `8b68b1b7115d77ac` | `8b68b1b7115d77ac` |  |
| `src/checks.py` | unchanged | `1590654cc85a2bdd` | `1590654cc85a2bdd` |  |
| `src/generate_data.py` | unchanged | `196e6c320d2bef31` | `196e6c320d2bef31` |  |
| `src/metrics.py` | new (declared) | `—` | `6b7f1defa8995c71` |  |
| `tests/test_baseline.py` | unchanged | `42fdf104d1dee96d` | `42fdf104d1dee96d` |  |
| `tests/test_integrity.py` | unchanged | `4613de2b419251b3` | `4613de2b419251b3` |  |
| `tests/test_metrics_unit.py` | new (declared) | `—` | `c9eedfe68178addb` |  |
| `tests/test_notebook_presentation.py` | new (declared) | `—` | `f0c0b199779f5893` |  |
| `tests/test_regression_f0.py` | new (declared) | `—` | `6ca9b1ffa9493191` |  |

## 47 metrics — 47 / 47 match

Values compared at the reference rounding of 6 decimals with no extra tolerance; numerators, denominators and descriptive fields (labels, unit, kind, population, numerator, denominator, time basis, definition reference) must be equal.

| Metric | F0 | F1 | abs. diff. | numerator F0 / F1 | denominator F0 / F1 | descriptive | match |
|---|---|---|---|---|---|---|---|
| `eligible_leads` | 7691 | 7691 | 0 | 7691 / 7691 | — / — | ✓ | ✓ |
| `mature_eligible_leads` | 6487 | 6487 | 0 | 6487 / 6487 | — / — | ✓ | ✓ |
| `duplicate_rows` | 154 | 154 | 0 | 154 / 154 | — / — | ✓ | ✓ |
| `reactivation_rows` | 100 | 100 | 0 | 100 / 100 | — / — | ✓ | ✓ |
| `share_manual_route` | 0.698739 | 0.698739 | 0.0 | 5374 / 5374 | 7691 / 7691 | ✓ | ✓ |
| `main_kpi_interviews_held_over_opportunities` | 0.450593 | 0.450593 | 0.0 | 2923 / 2923 | 6487 / 6487 | ✓ | ✓ |
| `held_rate_manual_route` | 0.313258 | 0.313258 | 0.0 | 1420 / 1420 | 4533 / 4533 | ✓ | ✓ |
| `held_rate_bot_route` | 0.769191 | 0.769191 | 0.0 | 1503 / 1503 | 1954 / 1954 | ✓ | ✓ |
| `booking_rate` | 0.562818 | 0.562818 | 0.0 | 3651 / 3651 | 6487 / 6487 | ✓ | ✓ |
| `show_rate_per_appointment` | 0.695661 | 0.695661 | 0.0 | 3431 / 3431 | 4932 / 4932 | ✓ | ✓ |
| `show_rate_per_appointment_manual` | 0.750338 | 0.750338 | 0.0 | 1665 / 1665 | 2219 / 2219 | ✓ | ✓ |
| `show_rate_per_appointment_bot` | 0.65094 | 0.65094 | 0.0 | 1766 / 1766 | 2713 / 2713 | ✓ | ✓ |
| `show_rate_per_lead` | 0.840426 | 0.840426 | 0.0 | 2923 / 2923 | 3478 / 3478 | ✓ | ✓ |
| `cancellation_rate` | 0.062179 | 0.062179 | 0.0 | 327 / 327 | 5259 / 5259 | ✓ | ✓ |
| `forms_over_interviews_held` | 0.429353 | 0.429353 | 0.0 | 1255 / 1255 | 2923 / 2923 | ✓ | ✓ |
| `enrollments_over_interviews_held` | 0.234006 | 0.234006 | 0.0 | 684 / 684 | 2923 / 2923 | ✓ | ✓ |
| `links_over_forms` | 0.830279 | 0.830279 | 0.0 | 1042 / 1042 | 1255 / 1255 | ✓ | ✓ |
| `enrollments_over_eligible_leads` | 0.105442 | 0.105442 | 0.0 | 684 / 684 | 6487 / 6487 | ✓ | ✓ |
| `sales_cycle_median_days` | 17.043947 | 17.043947 | 0.0 | — / — | 684 / 684 | ✓ | ✓ |
| `sales_cycle_mean_days` | 18.19736 | 18.19736 | 0.0 | — / — | 684 / 684 | ✓ | ✓ |
| `sla_first_attempt_24h_manual` | 0.697088 | 0.697088 | 0.0 | 3735 / 3735 | 5358 / 5358 | ✓ | ✓ |
| `sla_first_attempt_24h_manual_weekday` | 0.774053 | 0.774053 | 0.0 | 3371 / 3371 | 4355 / 4355 | ✓ | ✓ |
| `sla_first_attempt_24h_manual_weekend` | 0.362911 | 0.362911 | 0.0 | 364 / 364 | 1003 / 1003 | ✓ | ✓ |
| `sla_first_attempt_same_day_manual` | 0.356663 | 0.356663 | 0.0 | 1911 / 1911 | 5358 / 5358 | ✓ | ✓ |
| `first_response_median_hours` | 15.850278 | 15.850278 | 0.0 | — / — | 5243 / 5243 | ✓ | ✓ |
| `first_response_p90_hours` | 59.662778 | 59.662778 | 0.0 | — / — | 5243 / 5243 | ✓ | ✓ |
| `contact_rate` | 0.734503 | 0.734503 | 0.0 | 5486 / 5486 | 7469 / 7469 | ✓ | ✓ |
| `reassignment_rate_manual` | 0.219948 | 0.219948 | 0.0 | 1182 / 1182 | 5374 / 5374 | ✓ | ✓ |
| `bot_pre_interview_confirmation` | 0.998705 | 0.998705 | 0.0 | 2314 / 2314 | 2317 / 2317 | ✓ | ✓ |
| `bot_pre_interview_human_contact` | 0.481226 | 0.481226 | 0.0 | 1115 / 1115 | 2317 / 2317 | ✓ | ✓ |
| `followup_48h_manual_advisor` | 0.622392 | 0.622392 | 0.0 | 2118 / 2118 | 3403 / 3403 | ✓ | ✓ |
| `open_leads_at_snapshot` | 671 | 671 | 0 | 671 / 671 | — / — | ✓ | ✓ |
| `open_without_next_task` | 0.071535 | 0.071535 | 0.0 | 48 / 48 | 671 / 671 | ✓ | ✓ |
| `open_with_overdue_task` | 0.467958 | 0.467958 | 0.0 | 314 / 314 | 671 / 671 | ✓ | ✓ |
| `closed_lost_without_reason` | 0.029978 | 0.029978 | 0.0 | 187 / 187 | 6238 / 6238 | ✓ | ✓ |
| `lost_reason_share_iloc` | 0.344406 | 0.344406 | 0.0 | 2084 / 2084 | 6051 / 6051 | ✓ | ✓ |
| `advisor_months_over_150_realised` | 7 | 7 | 0 | 7 / 7 | 60 / 60 | ✓ | ✓ |
| `advisor_months_over_150_expected` | 4 | 4 | 0 | 4 / 4 | 60 / 60 | ✓ | ✓ |
| `enrollments_total` | 782 | 782 | 0 | 782 / 782 | — / — | ✓ | ✓ |
| `avg_net_price_eur` | 2521.835038 | 2521.835038 | 0.0 | — / — | 782 / 782 | ✓ | ✓ |
| `avg_net_price_single_eur` | 2301.986301 | 2301.986301 | 0.0 | — / — | 365 / 365 | ✓ | ✓ |
| `avg_net_price_installments_eur` | 2714.268585 | 2714.268585 | 0.0 | — / — | 417 / 417 | ✓ | ✓ |
| `installments_share` | 0.533248 | 0.533248 | 0.0 | 417 / 417 | 782 / 782 | ✓ | ✓ |
| `nurture_reactivation_complete_window` | 0.121951 | 0.121951 | 0.0 | 85 / 85 | 697 / 697 | ✓ | ✓ |
| `nurture_email_failure_rate` | 0.15095 | 0.15095 | 0.0 | 453 / 453 | 3001 / 3001 | ✓ | ✓ |
| `show_rate_with_personal_whatsapp` | 0.710867 | 0.710867 | 0.0 | 1099 / 1099 | 1546 / 1546 | ✓ | ✓ |
| `show_rate_without_personal_whatsapp` | 0.686898 | 0.686898 | 0.0 | 713 / 713 | 1038 / 1038 | ✓ | ✓ |
