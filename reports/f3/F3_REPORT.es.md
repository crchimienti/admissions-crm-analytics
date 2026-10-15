**Idioma:** [English](F3_REPORT.md) | Español

# F3.0 — informe de ejecución (`v1.3.1-f3`)

Generado por `python scripts/f3_run.py --check` · 2026-10-13 22:09 CEST.
Todos los datos y cifras son sintéticos (semilla 42 y el fixture oficial de 12 registros hecho a mano). Solo el perfil de admisiones; sin afirmaciones de portabilidad; sin CRM ni datos reales.

F3.0 declara ocho KPIs en `profiles/admissions/kpis.yaml` (kpi-spec/0.1, lenguaje cerrado: cinco operaciones, filtros solo con Y, sin expresiones, sin OR, sin código) y los evalúa con `src/kpispec` en paralelo con `src/metrics.py`, que sigue siendo la referencia oficial y no se modifica. Detalles: `docs/kpi_spec.es.md`.

## Versión

| Elemento | Valor |
|---|---|
| Identificador F3 | `v1.3.1-f3` |
| Tree id F3 (SHA-256 de `reports/f3/MANIFEST_F3.sha256`) | `f1a73209cfaf24d3768784e121f376e1d0ec485eca31ddd22f2b57e09ef23c34` |
| Referencias congeladas | `v1.0.0-f0` `eb4f60681f71e88a…` · `v1.1.0-f1` `9206c83e2b6fea80…` · `v1.2.3-f2` `a1df9fca9a38538f…` |
| Contrato / especificación | `crm-canonical/0.1.1` (sin cambios) · `kpi-spec/0.1` (nueva) |
| Git | sin commit ni tag (no es un repositorio git; no autorizado) |
| Entorno | python==3.13.16, numpy==2.5.3, pandas==3.0.5, pyyaml==6.0.3, matplotlib==3.11.2, nbformat==5.11.1, nbconvert==7.17.2, ipykernel==7.4.0, pytest==9.1.1 — idéntico a baseline/environment.txt |

## Comandos y resultados

| # | Comando | exit | segundos |
|---|---|---|---|
| 1 | `remove data/, notebook, build/, caches, reports/f3/ (except the v1.3.0 manifest)` | 0 | 0.0 |
| 2 | `python3 src/generate_data.py` | 0 | 4.5 |
| 3 | `python3 scripts/build_notebook.py` | 0 | 22.6 |
| 4 | `python3 scripts/map_to_canonical.py` | 0 | 2.3 |
| 5 | `python3 -m pytest -q` | 0 | 230.5 |

| Comprobación | Resultado |
|---|---|
| Pruebas | **409 passed, 0 failed, 0 xfailed, 0 xpassed** |
| Ocho KPIs del motor = F0, F1, F2 y src/metrics.py | **8 / 8** (valor a 6 decimales, numerador, denominador, campos descriptivos) |
| 47 métricas de src/metrics.py frente a F0, ruta directa / canónica | **47 / 47** · **47 / 47** |
| Documento F1 generado en memoria = reports/f1/metrics_f1.json (nunca se escribe) | idéntico byte a byte |
| Congelados: baseline/ (F0), reports/f1/ (F1), reports/f2/ (F2) | idénticos byte a byte antes y después; hashes fijados verificados (26 archivos) |
| Reproducibilidad | idéntica al manifiesto F3 guardado (137 archivos) — tree id f1a73209cfaf24d3 |

## Ocho KPIs con los datos generados

| KPI | valor de referencia (F0) | num. / den. | motor | = F0 | = F1 | = F2 | = metrics.py |
|---|---|---|---|---|---|---|---|
| `eligible_leads` | 7691 | 7691 / — | 7691 | ✓ | ✓ | ✓ | ✓ |
| `share_manual_route` | 0.698739 | 5374 / 7691 | 0.698739 | ✓ | ✓ | ✓ | ✓ |
| `main_kpi_interviews_held_over_opportunities` | 0.450593 | 2923 / 6487 | 0.450593 | ✓ | ✓ | ✓ | ✓ |
| `show_rate_per_appointment` | 0.695661 | 3431 / 4932 | 0.695661 | ✓ | ✓ | ✓ | ✓ |
| `forms_over_interviews_held` | 0.429353 | 1255 / 2923 | 0.429353 | ✓ | ✓ | ✓ | ✓ |
| `sla_first_attempt_24h_manual_weekend` | 0.362911 | 364 / 1003 | 0.362911 | ✓ | ✓ | ✓ | ✓ |
| `first_response_p90_hours` | 59.662778 | — / 5243 | 59.662778 | ✓ | ✓ | ✓ | ✓ |
| `sales_cycle_median_days` | 17.043947 | — / 684 | 17.043947 | ✓ | ✓ | ✓ | ✓ |

## Fixture oficial (12 registros), cinco variantes, solo el motor

| Variante | disponibles / no disponibles | no disponibles (motivo) | = valores a mano y matriz aprobada |
|---|---|---|---|
| `v_full` | 8 / 0 | — | ✓ |
| `v_milestone` | 8 / 0 | — | ✓ |
| `v_snapshot` | 6 / 2 | `main_kpi_interviews_held_over_opportunities` HM, `forms_over_interviews_held` HM | ✓ |
| `v_no_automated` | 6 / 2 | `sla_first_attempt_24h_manual_weekend` AUT, `first_response_p90_hours` AUT | ✓ |
| `v_no_appointments` | 7 / 1 | `show_rate_per_appointment` APT | ✓ |

## Elegibilidad, campos y ratios

En el perfil de admisiones, record_origin = original es exactamente la elegibilidad de F0 (is_duplicate = false e is_reactivation = false): el mapeo deriva record_origin de los dos indicadores y rechaza las filas con ambos. tests/test_kpi_eligibility.py y tests/test_kpi_requirements.py comprueban la equivalencia con los datos generados (frente al cargador de F0), por el camino canónico (CSV -> canónico -> adaptador), en el fixture de 12 registros y en las cinco variantes del fixture; un origen desconocido o nulo es un error de datos (E_ENUM en el contrato, K_FIELD_VALUE en el motor) y si falta el campo de origen el resultado es FLD, así que ningún registro entra en eligible sin avisar. Es una regla del perfil, no del motor.

Ningún campo se da por disponible: un campo no proporcionado da FLD con la lista exacta de campos que faltan, combinado con HM, HF, AUT, APT, DEN0, INSUF u ORD cuando corresponde. Los ratios exigen la misma unidad y una relación declarada (subset_of, same_base, independent_allowed); forms_over_interviews_held es same_base.

## Límites

Solo time_model naive_wall_clock: los instantes UTC y las reglas de calendario local son F3.5 (decidida, todavía no autorizada; F3.0 no contiene código UTC); el adaptador UTC sigue sin estar soportado. Los otros 27 KPIs parametrizables son F3.1 (no autorizada). No se afirma preparación para datos reales ni para conexiones CRM.

## Archivos frente a F2 (`reports/f2/MANIFEST_F2.sha256`, `v1.2.3-f2`)

modified (declared): 6, new (declared): 21, unchanged: 97. Modificados:

- `README.es.md` — sección F3.0, estructura y cómo ejecutar (ninguna cifra cambia)
- `README.md` — F3.0 section, structure and how to run (no figure changed)
- `docs/PROJECT_STATUS.es.md` — estado de F3.0, F3.5 en la hoja de ruta, motivo FLD, F2 congelada
- `docs/PROJECT_STATUS.md` — F3.0 state, F3.5 in the roadmap, FLD reason, frozen F2
- `scripts/f2_run.py` — guard only: refuses to run on the F3 tree before touching any file (reports/f2/ is frozen)
- `src/canonical/adapters/admissions.py` — first_human_attempt extracted as a reusable profile function; metrics imported lazily (same results)

Nuevos:

- `docs/kpi_spec.es.md`
- `docs/kpi_spec.md`
- `profiles/admissions/kpis.yaml`
- `reports/f3/MANIFEST_F3_v1.3.0.sha256`
- `reports/f3/kpi_engine_results.json`
- `reports/f3/kpi_handcalc_variants.json`
- `schema/kpi_spec_v0.1.yaml`
- `scripts/f3_run.py`
- `src/kpispec/__init__.py`
- `src/kpispec/engine.py`
- `src/kpispec/fields.py`
- `src/kpispec/spec.py`
- `tests/kpi_helpers.py`
- `tests/test_kpi_eligibility.py`
- `tests/test_kpi_engine_ops.py`
- `tests/test_kpi_handcalc.py`
- `tests/test_kpi_isolation.py`
- `tests/test_kpi_regression.py`
- `tests/test_kpi_requirements.py`
- `tests/test_kpi_spec_schema.py`
- `tests/test_regression_f2.py`

Intactos (idénticos byte a byte a F2):

- `.gitignore`
- `baseline/BASELINE.es.md`
- `baseline/BASELINE.md`
- `baseline/F0_REPORT.es.md`
- `baseline/F0_REPORT.md`
- `baseline/MANIFEST.sha256`
- `baseline/environment.txt`
- `baseline/metrics_v1.json`
- `config/simulation_params.yaml`
- `data/activities.csv`
- `data/dq_ground_truth.csv`
- `data/leads.csv`
- `docs/assumptions.es.md`
- `docs/assumptions.md`
- `docs/canonical_schema.es.md`
- `docs/canonical_schema.md`
- `docs/data_dictionary.es.md`
- `docs/data_dictionary.md`
- `docs/kpi_definitions.es.md`
- `docs/kpi_definitions.md`
- `notebooks/admissions_analysis.ipynb`
- `profiles/admissions/kpi_requirements.yaml`
- `profiles/admissions/mapping_csv_v1.yaml`
- `profiles/admissions/rules.yaml`
- `reports/f1/F0_COMPARISON.es.md`
- `reports/f1/F0_COMPARISON.md`
- `reports/f1/F1_REPORT.es.md`
- `reports/f1/F1_REPORT.md`
- `reports/f1/MANIFEST_F1.sha256`
- `reports/f1/metrics_f1.json`
- `requirements.txt`
- `schema/canonical_v0.1.1.yaml`
- `schema/canonical_v0.1.yaml`
- `scripts/build_notebook.py`
- `scripts/export_metrics.py`
- `scripts/f0_baseline.py`
- `scripts/f1_run.py`
- `scripts/map_to_canonical.py`
- `scripts/notebook_conclusions.md`
- `src/calendar_utils.py`
- `src/canonical/__init__.py`
- `src/canonical/adapters/__init__.py`
- `src/canonical/availability.py`
- `src/canonical/contract.py`
- `src/canonical/history.py`
- `src/canonical/mapping.py`
- `src/canonical/validate.py`
- `src/checks.py`
- `src/generate_data.py`
- `src/metrics.py`
- `tests/fixtures/canonical_handcalc/expected.json`
- `tests/fixtures/canonical_handcalc/v_full/activities.csv`
- `tests/fixtures/canonical_handcalc/v_full/appointments.csv`
- `tests/fixtures/canonical_handcalc/v_full/dataset.csv`
- `tests/fixtures/canonical_handcalc/v_full/record_attributes.csv`
- `tests/fixtures/canonical_handcalc/v_full/records.csv`
- `tests/fixtures/canonical_handcalc/v_full/stage_events.csv`
- `tests/fixtures/canonical_handcalc/v_milestone/activities.csv`
- `tests/fixtures/canonical_handcalc/v_milestone/appointments.csv`
- `tests/fixtures/canonical_handcalc/v_milestone/dataset.csv`
- `tests/fixtures/canonical_handcalc/v_milestone/record_attributes.csv`
- `tests/fixtures/canonical_handcalc/v_milestone/records.csv`
- `tests/fixtures/canonical_handcalc/v_milestone/stage_events.csv`
- `tests/fixtures/canonical_handcalc/v_no_appointments/activities.csv`
- `tests/fixtures/canonical_handcalc/v_no_appointments/dataset.csv`
- `tests/fixtures/canonical_handcalc/v_no_appointments/record_attributes.csv`
- `tests/fixtures/canonical_handcalc/v_no_appointments/records.csv`
- `tests/fixtures/canonical_handcalc/v_no_appointments/stage_events.csv`
- `tests/fixtures/canonical_handcalc/v_no_automated/activities.csv`
- `tests/fixtures/canonical_handcalc/v_no_automated/appointments.csv`
- `tests/fixtures/canonical_handcalc/v_no_automated/dataset.csv`
- `tests/fixtures/canonical_handcalc/v_no_automated/record_attributes.csv`
- `tests/fixtures/canonical_handcalc/v_no_automated/records.csv`
- `tests/fixtures/canonical_handcalc/v_no_automated/stage_events.csv`
- `tests/fixtures/canonical_handcalc/v_snapshot/activities.csv`
- `tests/fixtures/canonical_handcalc/v_snapshot/appointments.csv`
- `tests/fixtures/canonical_handcalc/v_snapshot/dataset.csv`
- `tests/fixtures/canonical_handcalc/v_snapshot/record_attributes.csv`
- `tests/fixtures/canonical_handcalc/v_snapshot/records.csv`
- `tests/fixtures/mapping_errors/base/activities.csv`
- `tests/fixtures/mapping_errors/base/leads.csv`
- `tests/fixtures/mapping_errors/cases.yaml`
- `tests/fixtures/timezones/cases.yaml`
- `tests/test_baseline.py`
- `tests/test_canonical_availability.py`
- `tests/test_canonical_contract.py`
- `tests/test_canonical_event_order.py`
- `tests/test_canonical_handcalc.py`
- `tests/test_canonical_mapping.py`
- `tests/test_canonical_mapping_errors.py`
- `tests/test_canonical_timestamps.py`
- `tests/test_integrity.py`
- `tests/test_metrics_robustness.py`
- `tests/test_metrics_unit.py`
- `tests/test_notebook_presentation.py`
- `tests/test_regression_f0.py`
- `tests/test_regression_f1.py`

Hashes por archivo: [`F2_COMPARISON.es.md`](F2_COMPARISON.es.md).

## Cambios frente a `v1.3.0-f3` (`reports/f3/MANIFEST_F3_v1.3.0.sha256`, tree id `b189d44e9d092d34…`, fijado)

modified (declared): 15, new (declared): 1, unchanged: 108. Modificados:

- `README.es.md` — encabezado de versión
- `README.md` — version heading
- `docs/PROJECT_STATUS.es.md` — fila v1.3.1-f3; diseño completo de F3.5, todavía no autorizada; elegibilidad en todas las variantes
- `docs/PROJECT_STATUS.md` — v1.3.1-f3 row; full F3.5 design, not yet authorised; eligibility on all variants
- `docs/kpi_spec.es.md` — versión; sin importar metrics ni indirectamente; HF en campos de etapa
- `docs/kpi_spec.md` — version; no metrics import even indirectly; HF for stage fields
- `reports/f3/kpi_engine_results.json` — version_id and the route note (same results)
- `scripts/f3_run.py` — v1.3.1-f3: keeps and pins the v1.3.0 manifest, classifies against it, lists intact files
- `src/canonical/adapters/admissions.py` — src/metrics.py imported lazily, only by the metrics route (the engine no longer loads it, even indirectly); same results
- `src/kpispec/fields.py` — stage fields with if_missing: HF need full history; via-appointment fields combine APT and FLD
- `tests/test_kpi_engine_ops.py` — HF, FLD+HM and ORD tests
- `tests/test_kpi_handcalc.py` — runs in a fresh interpreter without loading src/metrics.py
- `tests/test_kpi_isolation.py` — subprocess check: neither src/metrics.py nor the generator is loaded; no subprocess/os in src/kpispec
- `tests/test_kpi_requirements.py` — eligibility equivalence on all five variants; missing field -> FLD or its capability reason; a null row is not FLD
- `tests/test_regression_f2.py` — declared change text of the adapter updated

Nuevos:

- `reports/f3/MANIFEST_F3_v1.3.0.sha256`

Todos los demás archivos son idénticos byte a byte a `v1.3.0-f3`.
