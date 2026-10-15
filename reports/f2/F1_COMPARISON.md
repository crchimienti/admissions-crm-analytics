**Language:** English | [Español](F1_COMPARISON.es.md)

# v1.2.3-f2 vs F1 — files and the 47 metrics before and after

Reference: `v1.1.0-f1` (`reports/f1/MANIFEST_F1.sha256`, tree id `9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651`). Hashes truncated to 16 characters.

## 47 metrics — canonical vs F0 47/47 · vs F1 47/47 · direct vs F0 47/47

Before: F0 (baseline/metrics_v1.json) and F1 (reports/f1/metrics_f1.json). After: this revision, direct route (src/metrics.py on the CSV files) and canonical route (CSV → canonical dataset, contract 0.1.1 → adapter → src/metrics.py). Values at the reference rounding of 6 decimals with no extra tolerance; numerators, denominators and descriptive fields must also be equal.

| Metric | F0 | F1 | after, direct | after, canonical | num. / den. after | canonical = F0 | canonical = F1 | direct = F0 |
|---|---|---|---|---|---|---|---|---|
| `eligible_leads` | 7691 | 7691 | 7691 | 7691 | 7691 / — | ✓ | ✓ | ✓ |
| `mature_eligible_leads` | 6487 | 6487 | 6487 | 6487 | 6487 / — | ✓ | ✓ | ✓ |
| `duplicate_rows` | 154 | 154 | 154 | 154 | 154 / — | ✓ | ✓ | ✓ |
| `reactivation_rows` | 100 | 100 | 100 | 100 | 100 / — | ✓ | ✓ | ✓ |
| `share_manual_route` | 0.698739 | 0.698739 | 0.698739 | 0.698739 | 5374 / 7691 | ✓ | ✓ | ✓ |
| `main_kpi_interviews_held_over_opportunities` | 0.450593 | 0.450593 | 0.450593 | 0.450593 | 2923 / 6487 | ✓ | ✓ | ✓ |
| `held_rate_manual_route` | 0.313258 | 0.313258 | 0.313258 | 0.313258 | 1420 / 4533 | ✓ | ✓ | ✓ |
| `held_rate_bot_route` | 0.769191 | 0.769191 | 0.769191 | 0.769191 | 1503 / 1954 | ✓ | ✓ | ✓ |
| `booking_rate` | 0.562818 | 0.562818 | 0.562818 | 0.562818 | 3651 / 6487 | ✓ | ✓ | ✓ |
| `show_rate_per_appointment` | 0.695661 | 0.695661 | 0.695661 | 0.695661 | 3431 / 4932 | ✓ | ✓ | ✓ |
| `show_rate_per_appointment_manual` | 0.750338 | 0.750338 | 0.750338 | 0.750338 | 1665 / 2219 | ✓ | ✓ | ✓ |
| `show_rate_per_appointment_bot` | 0.65094 | 0.65094 | 0.65094 | 0.65094 | 1766 / 2713 | ✓ | ✓ | ✓ |
| `show_rate_per_lead` | 0.840426 | 0.840426 | 0.840426 | 0.840426 | 2923 / 3478 | ✓ | ✓ | ✓ |
| `cancellation_rate` | 0.062179 | 0.062179 | 0.062179 | 0.062179 | 327 / 5259 | ✓ | ✓ | ✓ |
| `forms_over_interviews_held` | 0.429353 | 0.429353 | 0.429353 | 0.429353 | 1255 / 2923 | ✓ | ✓ | ✓ |
| `enrollments_over_interviews_held` | 0.234006 | 0.234006 | 0.234006 | 0.234006 | 684 / 2923 | ✓ | ✓ | ✓ |
| `links_over_forms` | 0.830279 | 0.830279 | 0.830279 | 0.830279 | 1042 / 1255 | ✓ | ✓ | ✓ |
| `enrollments_over_eligible_leads` | 0.105442 | 0.105442 | 0.105442 | 0.105442 | 684 / 6487 | ✓ | ✓ | ✓ |
| `sales_cycle_median_days` | 17.043947 | 17.043947 | 17.043947 | 17.043947 | — / 684 | ✓ | ✓ | ✓ |
| `sales_cycle_mean_days` | 18.19736 | 18.19736 | 18.19736 | 18.19736 | — / 684 | ✓ | ✓ | ✓ |
| `sla_first_attempt_24h_manual` | 0.697088 | 0.697088 | 0.697088 | 0.697088 | 3735 / 5358 | ✓ | ✓ | ✓ |
| `sla_first_attempt_24h_manual_weekday` | 0.774053 | 0.774053 | 0.774053 | 0.774053 | 3371 / 4355 | ✓ | ✓ | ✓ |
| `sla_first_attempt_24h_manual_weekend` | 0.362911 | 0.362911 | 0.362911 | 0.362911 | 364 / 1003 | ✓ | ✓ | ✓ |
| `sla_first_attempt_same_day_manual` | 0.356663 | 0.356663 | 0.356663 | 0.356663 | 1911 / 5358 | ✓ | ✓ | ✓ |
| `first_response_median_hours` | 15.850278 | 15.850278 | 15.850278 | 15.850278 | — / 5243 | ✓ | ✓ | ✓ |
| `first_response_p90_hours` | 59.662778 | 59.662778 | 59.662778 | 59.662778 | — / 5243 | ✓ | ✓ | ✓ |
| `contact_rate` | 0.734503 | 0.734503 | 0.734503 | 0.734503 | 5486 / 7469 | ✓ | ✓ | ✓ |
| `reassignment_rate_manual` | 0.219948 | 0.219948 | 0.219948 | 0.219948 | 1182 / 5374 | ✓ | ✓ | ✓ |
| `bot_pre_interview_confirmation` | 0.998705 | 0.998705 | 0.998705 | 0.998705 | 2314 / 2317 | ✓ | ✓ | ✓ |
| `bot_pre_interview_human_contact` | 0.481226 | 0.481226 | 0.481226 | 0.481226 | 1115 / 2317 | ✓ | ✓ | ✓ |
| `followup_48h_manual_advisor` | 0.622392 | 0.622392 | 0.622392 | 0.622392 | 2118 / 3403 | ✓ | ✓ | ✓ |
| `open_leads_at_snapshot` | 671 | 671 | 671 | 671 | 671 / — | ✓ | ✓ | ✓ |
| `open_without_next_task` | 0.071535 | 0.071535 | 0.071535 | 0.071535 | 48 / 671 | ✓ | ✓ | ✓ |
| `open_with_overdue_task` | 0.467958 | 0.467958 | 0.467958 | 0.467958 | 314 / 671 | ✓ | ✓ | ✓ |
| `closed_lost_without_reason` | 0.029978 | 0.029978 | 0.029978 | 0.029978 | 187 / 6238 | ✓ | ✓ | ✓ |
| `lost_reason_share_iloc` | 0.344406 | 0.344406 | 0.344406 | 0.344406 | 2084 / 6051 | ✓ | ✓ | ✓ |
| `advisor_months_over_150_realised` | 7 | 7 | 7 | 7 | 7 / 60 | ✓ | ✓ | ✓ |
| `advisor_months_over_150_expected` | 4 | 4 | 4 | 4 | 4 / 60 | ✓ | ✓ | ✓ |
| `enrollments_total` | 782 | 782 | 782 | 782 | 782 / — | ✓ | ✓ | ✓ |
| `avg_net_price_eur` | 2521.835038 | 2521.835038 | 2521.835038 | 2521.835038 | — / 782 | ✓ | ✓ | ✓ |
| `avg_net_price_single_eur` | 2301.986301 | 2301.986301 | 2301.986301 | 2301.986301 | — / 365 | ✓ | ✓ | ✓ |
| `avg_net_price_installments_eur` | 2714.268585 | 2714.268585 | 2714.268585 | 2714.268585 | — / 417 | ✓ | ✓ | ✓ |
| `installments_share` | 0.533248 | 0.533248 | 0.533248 | 0.533248 | 417 / 782 | ✓ | ✓ | ✓ |
| `nurture_reactivation_complete_window` | 0.121951 | 0.121951 | 0.121951 | 0.121951 | 85 / 697 | ✓ | ✓ | ✓ |
| `nurture_email_failure_rate` | 0.15095 | 0.15095 | 0.15095 | 0.15095 | 453 / 3001 | ✓ | ✓ | ✓ |
| `show_rate_with_personal_whatsapp` | 0.710867 | 0.710867 | 0.710867 | 0.710867 | 1099 / 1546 | ✓ | ✓ | ✓ |
| `show_rate_without_personal_whatsapp` | 0.686898 | 0.686898 | 0.686898 | 0.686898 | 713 / 1038 | ✓ | ✓ | ✓ |

## Files

| File | Status | SHA-256 F1 | SHA-256 v1.2.3-f2 | Declared change |
|---|---|---|---|---|
| `.gitignore` | unchanged | `b9e0ad01d09ecce2` | `b9e0ad01d09ecce2` |  |
| `README.es.md` | modified (declared) | `925c03b7bc25faf6` | `90227b839d932d3a` | sección F2, estructura y cómo ejecutar (ninguna cifra cambia) |
| `README.md` | modified (declared) | `d506000a42669b5d` | `1ce7b39c4463bddf` | F2 section, repository structure and how to run (no figure changed) |
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
| `docs/PROJECT_STATUS.es.md` | new (declared) | `—` | `bff4e1f9882b7f2b` |  |
| `docs/PROJECT_STATUS.md` | new (declared) | `—` | `15c657f909c33983` |  |
| `docs/assumptions.es.md` | unchanged | `43040e6e83651a3b` | `43040e6e83651a3b` |  |
| `docs/assumptions.md` | unchanged | `cd7953a731187b4a` | `cd7953a731187b4a` |  |
| `docs/canonical_schema.es.md` | new (declared) | `—` | `5a50fb62cc69a9fd` |  |
| `docs/canonical_schema.md` | new (declared) | `—` | `4ef48f29cf54fdaa` |  |
| `docs/data_dictionary.es.md` | unchanged | `f4660bdf0e77b500` | `f4660bdf0e77b500` |  |
| `docs/data_dictionary.md` | unchanged | `6095fc6c5eb1ba45` | `6095fc6c5eb1ba45` |  |
| `docs/kpi_definitions.es.md` | unchanged | `9b744adda9dc09f8` | `9b744adda9dc09f8` |  |
| `docs/kpi_definitions.md` | unchanged | `2c20dafad010a445` | `2c20dafad010a445` |  |
| `notebooks/admissions_analysis.ipynb` | unchanged | `d40074d45d635b18` | `d40074d45d635b18` |  |
| `profiles/admissions/kpi_requirements.yaml` | new (declared) | `—` | `22814b123979080e` |  |
| `profiles/admissions/mapping_csv_v1.yaml` | new (declared) | `—` | `71047beac704ab6b` |  |
| `profiles/admissions/rules.yaml` | new (declared) | `—` | `0dc2d22c0ff756b0` |  |
| `reports/f2/MANIFEST_F2_v1.2.0.sha256` | new (declared) | `—` | `2ba1a33f9001b613` |  |
| `reports/f2/MANIFEST_F2_v1.2.1.sha256` | new (declared) | `—` | `f71ca2471525fbaa` |  |
| `reports/f2/MANIFEST_F2_v1.2.2.sha256` | new (declared) | `—` | `ddfc93cf87313a3b` |  |
| `reports/f2/canonical_admissions.sha256` | new (declared) | `—` | `d9905805f678650b` |  |
| `reports/f2/handcalc_variants.json` | new (declared) | `—` | `7eb2421b29e789e4` |  |
| `reports/f2/metrics_f2_canonical.json` | new (declared) | `—` | `eaa32bdda075d587` |  |
| `requirements.txt` | unchanged | `fea7aa31645369df` | `fea7aa31645369df` |  |
| `schema/canonical_v0.1.1.yaml` | new (declared) | `—` | `a9cf44c1e2940f25` |  |
| `schema/canonical_v0.1.yaml` | new (declared) | `—` | `0d2fff9114ee1c72` |  |
| `scripts/build_notebook.py` | unchanged | `579d547a100d7db9` | `579d547a100d7db9` |  |
| `scripts/export_metrics.py` | modified (declared) | `e30b3427b759278d` | `cea4e580d7324d12` | guard only: refuses to write reports/f1/ on the F2 tree |
| `scripts/f0_baseline.py` | unchanged | `61b821c085e31b16` | `61b821c085e31b16` |  |
| `scripts/f1_run.py` | modified (declared) | `352fd74878b4dea8` | `b414a6dbb4acd537` | guard only: refuses to run on the F2 tree (reports/f1/ is frozen) |
| `scripts/f2_run.py` | new (declared) | `—` | `e686223554fd1b8c` |  |
| `scripts/map_to_canonical.py` | new (declared) | `—` | `c74e0406368ad01e` |  |
| `scripts/notebook_conclusions.md` | unchanged | `d2f5c04e765b4380` | `d2f5c04e765b4380` |  |
| `src/calendar_utils.py` | unchanged | `8b68b1b7115d77ac` | `8b68b1b7115d77ac` |  |
| `src/canonical/__init__.py` | new (declared) | `—` | `bb0f52397274a32d` |  |
| `src/canonical/adapters/__init__.py` | new (declared) | `—` | `7841a227f12c736e` |  |
| `src/canonical/adapters/admissions.py` | new (declared) | `—` | `3779a20cdd9d85fc` |  |
| `src/canonical/availability.py` | new (declared) | `—` | `415d8da889499dca` |  |
| `src/canonical/contract.py` | new (declared) | `—` | `b9f01a748e46b965` |  |
| `src/canonical/history.py` | new (declared) | `—` | `86aed0f55c67b469` |  |
| `src/canonical/mapping.py` | new (declared) | `—` | `2439c04dd51fcbba` |  |
| `src/canonical/validate.py` | new (declared) | `—` | `a2a410d1dccab7f6` |  |
| `src/checks.py` | unchanged | `1590654cc85a2bdd` | `1590654cc85a2bdd` |  |
| `src/generate_data.py` | unchanged | `196e6c320d2bef31` | `196e6c320d2bef31` |  |
| `src/metrics.py` | modified (declared) | `6b7f1defa8995c71` | `c5503ccd4ac5d965` | authorised v1.2.1-f2 robustness fix (zero denominators, empty appointment structures); same 47 values |
| `tests/fixtures/canonical_handcalc/expected.json` | new (declared) | `—` | `7436336bd60f551d` |  |
| `tests/fixtures/canonical_handcalc/v_full/activities.csv` | new (declared) | `—` | `664969dc30d7e1ec` |  |
| `tests/fixtures/canonical_handcalc/v_full/appointments.csv` | new (declared) | `—` | `d9148a4d2fb33feb` |  |
| `tests/fixtures/canonical_handcalc/v_full/dataset.csv` | new (declared) | `—` | `c807cda16d0710c7` |  |
| `tests/fixtures/canonical_handcalc/v_full/record_attributes.csv` | new (declared) | `—` | `de5b816a04b578c5` |  |
| `tests/fixtures/canonical_handcalc/v_full/records.csv` | new (declared) | `—` | `c198070f0cb628a5` |  |
| `tests/fixtures/canonical_handcalc/v_full/stage_events.csv` | new (declared) | `—` | `50fb386c196709a8` |  |
| `tests/fixtures/canonical_handcalc/v_milestone/activities.csv` | new (declared) | `—` | `664969dc30d7e1ec` |  |
| `tests/fixtures/canonical_handcalc/v_milestone/appointments.csv` | new (declared) | `—` | `d9148a4d2fb33feb` |  |
| `tests/fixtures/canonical_handcalc/v_milestone/dataset.csv` | new (declared) | `—` | `fd3a732341d1165b` |  |
| `tests/fixtures/canonical_handcalc/v_milestone/record_attributes.csv` | new (declared) | `—` | `de5b816a04b578c5` |  |
| `tests/fixtures/canonical_handcalc/v_milestone/records.csv` | new (declared) | `—` | `c198070f0cb628a5` |  |
| `tests/fixtures/canonical_handcalc/v_milestone/stage_events.csv` | new (declared) | `—` | `f46ac23d714e1be1` |  |
| `tests/fixtures/canonical_handcalc/v_no_appointments/activities.csv` | new (declared) | `—` | `664969dc30d7e1ec` |  |
| `tests/fixtures/canonical_handcalc/v_no_appointments/dataset.csv` | new (declared) | `—` | `7964cc570ba418d2` |  |
| `tests/fixtures/canonical_handcalc/v_no_appointments/record_attributes.csv` | new (declared) | `—` | `de5b816a04b578c5` |  |
| `tests/fixtures/canonical_handcalc/v_no_appointments/records.csv` | new (declared) | `—` | `c198070f0cb628a5` |  |
| `tests/fixtures/canonical_handcalc/v_no_appointments/stage_events.csv` | new (declared) | `—` | `50fb386c196709a8` |  |
| `tests/fixtures/canonical_handcalc/v_no_automated/activities.csv` | new (declared) | `—` | `696116c90e2a730d` |  |
| `tests/fixtures/canonical_handcalc/v_no_automated/appointments.csv` | new (declared) | `—` | `53c5f091c828f0e8` |  |
| `tests/fixtures/canonical_handcalc/v_no_automated/dataset.csv` | new (declared) | `—` | `e59294929c066dcc` |  |
| `tests/fixtures/canonical_handcalc/v_no_automated/record_attributes.csv` | new (declared) | `—` | `de5b816a04b578c5` |  |
| `tests/fixtures/canonical_handcalc/v_no_automated/records.csv` | new (declared) | `—` | `c198070f0cb628a5` |  |
| `tests/fixtures/canonical_handcalc/v_no_automated/stage_events.csv` | new (declared) | `—` | `50fb386c196709a8` |  |
| `tests/fixtures/canonical_handcalc/v_snapshot/activities.csv` | new (declared) | `—` | `664969dc30d7e1ec` |  |
| `tests/fixtures/canonical_handcalc/v_snapshot/appointments.csv` | new (declared) | `—` | `d9148a4d2fb33feb` |  |
| `tests/fixtures/canonical_handcalc/v_snapshot/dataset.csv` | new (declared) | `—` | `05ce53a84a6ef611` |  |
| `tests/fixtures/canonical_handcalc/v_snapshot/record_attributes.csv` | new (declared) | `—` | `de5b816a04b578c5` |  |
| `tests/fixtures/canonical_handcalc/v_snapshot/records.csv` | new (declared) | `—` | `c198070f0cb628a5` |  |
| `tests/fixtures/mapping_errors/base/activities.csv` | new (declared) | `—` | `8fd6d38afd45b875` |  |
| `tests/fixtures/mapping_errors/base/leads.csv` | new (declared) | `—` | `1e22aa4fca09de80` |  |
| `tests/fixtures/mapping_errors/cases.yaml` | new (declared) | `—` | `72dc5c56012a091c` |  |
| `tests/fixtures/timezones/cases.yaml` | new (declared) | `—` | `0cc974a278cc8f08` |  |
| `tests/test_baseline.py` | unchanged | `42fdf104d1dee96d` | `42fdf104d1dee96d` |  |
| `tests/test_canonical_availability.py` | new (declared) | `—` | `50776fda3bf09247` |  |
| `tests/test_canonical_contract.py` | new (declared) | `—` | `c85afa00aec6320f` |  |
| `tests/test_canonical_event_order.py` | new (declared) | `—` | `e5aa2a29371980b2` |  |
| `tests/test_canonical_handcalc.py` | new (declared) | `—` | `db677bcadf4246b7` |  |
| `tests/test_canonical_mapping.py` | new (declared) | `—` | `9ce56510c2ad88d6` |  |
| `tests/test_canonical_mapping_errors.py` | new (declared) | `—` | `6dedc57d0afd90f8` |  |
| `tests/test_canonical_timestamps.py` | new (declared) | `—` | `0ded880f8cf25f86` |  |
| `tests/test_integrity.py` | unchanged | `4613de2b419251b3` | `4613de2b419251b3` |  |
| `tests/test_metrics_robustness.py` | new (declared) | `—` | `bb9f402796be164b` |  |
| `tests/test_metrics_unit.py` | unchanged | `c9eedfe68178addb` | `c9eedfe68178addb` |  |
| `tests/test_notebook_presentation.py` | unchanged | `f0c0b199779f5893` | `f0c0b199779f5893` |  |
| `tests/test_regression_f0.py` | unchanged | `6ca9b1ffa9493191` | `6ca9b1ffa9493191` |  |
| `tests/test_regression_f1.py` | new (declared) | `—` | `f742875423d7cd5b` |  |
