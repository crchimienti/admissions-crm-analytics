**Idioma:** [English](F2_REPORT.md) | Español

# F2 — informe de ejecución (`v1.2.3-f2`)

Generado por `python scripts/f2_run.py --check` · 2026-10-13 19:34 CEST.
Todos los datos y cifras son sintéticos (semilla 42 y un fixture construido a mano). Alcance: solo el perfil de admisiones; sin afirmaciones de portabilidad; sin conexión a ningún CRM.

**Cierre de F2 (corrección de documentación).** Esta entrega corrige solo documentación de v1.2.2-f2 (aprobada como versión de trabajo de F2): el informe ya no contiene el párrafo obsoleto sobre el contrato y PROJECT_STATUS separa las restricciones vigentes de los objetivos futuros. Cálculos, fixtures, datos y contrato (crm-canonical/0.1.1) no cambian. Sustituye a `v1.2.2-f2` (tree id `ddfc93cf87313a3b…`, manifiesto conservado en `reports/f2/MANIFEST_F2_v1.2.2.sha256`).

## Versión

| Elemento | Valor |
|---|---|
| Identificador F2 | `v1.2.3-f2` |
| Tree id F2 (SHA-256 de `reports/f2/MANIFEST_F2.sha256`) | `a1df9fca9a38538f912fadfb437b4831f609962baa7b97fe763f68ec7a0885db` |
| Referencias | `v1.0.0-f0` `eb4f60681f71e88a…` · `v1.1.0-f1` `9206c83e2b6fea80…` · `v1.2.0-f2` `2ba1a33f9001b613…` · `v1.2.1-f2` `f71ca2471525fbaa…` · `v1.2.2-f2` `ddfc93cf87313a3b…` |
| Contrato canónico | `crm-canonical/0.1.1` (`schema/canonical_v0.1.1.yaml`; revisión aditiva de 0.1: stage_events.seq opcional y reglas C08-C09) |
| Git | sin commit ni tag (no es un repositorio git; no autorizado) |
| Entorno | python==3.13.16, numpy==2.5.3, pandas==3.0.5, pyyaml==6.0.3, matplotlib==3.11.2, nbformat==5.11.1, nbconvert==7.17.2, ipykernel==7.4.0, pytest==9.1.1 — idéntico a baseline/environment.txt |

## Comandos y resultados

| # | Comando | exit | segundos |
|---|---|---|---|
| 1 | `remove data/, notebook, build/, caches, generated reports/f2 files` | 0 | 0.0 |
| 2 | `python3 src/generate_data.py` | 0 | 4.7 |
| 3 | `python3 scripts/build_notebook.py` | 0 | 24.6 |
| 4 | `python3 scripts/map_to_canonical.py` | 0 | 2.6 |
| 5 | `python3 -m pytest -q` | 0 | 214.1 |

| Comprobación | Resultado |
|---|---|
| Pruebas | **326 passed, 0 failed, 0 xfailed, 0 xpassed** |
| Ruta directa: documento de métricas de F1 generado en memoria por src/metrics.py y comparado con reports/f1/metrics_f1.json (que nunca se escribe) | idéntico byte a byte |
| 47 métricas, ruta directa frente a F0 | **47 / 47** |
| 47 métricas, ruta canónica frente a F0 / F1 | **47 / 47** · **47 / 47** (ids, orden, campos descriptivos, numeradores, denominadores, valores a 6 decimales) |
| Congelados: baseline/ (F0), reports/f1/ (F1), manifiestos v1.2.0-f2, v1.2.1-f2 y v1.2.2-f2 | idénticos byte a byte antes y después; ids congelados verificados (16 archivos) |
| Reproducibilidad | idéntica al manifiesto F2 guardado (109 archivos) — tree id a1df9fca9a38538f |

Valor a valor, las 47 métricas antes (F0, F1) y después (esta revisión, ambas rutas) están en [`F1_COMPARISON.es.md`](F1_COMPARISON.es.md).

## Orden de eventos y contrato (v1.2.2-f2)

La especificación aprobada de stage_events (clave record_id + seq; obligatorios record_id, seq, stage, entered_at, event_kind; opcionales exited_at, changed_by_type; seq ordena los timestamps iguales) se mapea columna a columna en docs/canonical_schema.es.md §11.3. El contrato pasa a crm-canonical/0.1.1, una revisión aditiva: un seq opcional conserva el orden de la fuente y es único por registro y coherente con occurred_at (C08). Sin seq, los eventos de un registro con el mismo occurred_at tienen un orden indeterminado (C09); nunca se resuelve por etapa, event_id ni posición en el archivo (se ha eliminado el desempate por event_id que v1.2.1-f2 usaba dentro de time_in_stage). Solo time_in_stage depende del orden y entonces es not_available con motivo ORD. Retrocesos, reaperturas, conteos de entradas y primeras entradas no dependen del orden: tests/test_canonical_event_order.py lo comprueba con eventos simultáneos, filas barajadas e ids renombrados. exited_at y changed_by_type no se representan (§11.3). El CSV de admisiones no da ningún orden, así que su mapeo sigue emitiendo datasets crm-canonical/0.1 sin seq, que 0.1.1 acepta.

current_status no es el status = open/won/lost aprobado: conserva los estados operativos del perfil (new, working, iloc_sequence, nurture, closed_won, closed_lost). El resultado se deriva solo de current_stage (closed_won → ganado, closed_lost → perdido, el resto → abierto), así que un registro en nurture está perdido y nunca es un cuarto resultado; comprobado en el fixture y en los datos generados (docs §11.2).

## Defectos de robustez corregidos en src/metrics.py (autorizado, v1.2.1-f2)

| Defecto en v1.2.0-f2 | Entrada que lo provocaba | Corrección |
|---|---|---|
| MP1 `ZeroDivisionError` `forms_over_interviews_held`; posible inf en otras razones | ningún lead maduro con entrevista realizada | todas las razones de baseline_metrics y directional_rates por rate() → NaN → DEN0 |
| MP3 `TypeError` `Context.bot_pre` | ninguna fila de citas | búsqueda de la franja con reindex (se conserva el tipo fecha) |
| MP3b `TypeError` `show_rate_per_lead` | ninguna fila de citas | Context.showlead con tipo bool |
| MP4 `AttributeError` `Context.personal_wa_appointments` | ninguna cita realizada / no-show desde el 2025-07-01 | columna booleana tipada |

No cambia ninguna definición. El adaptador separa ahora tres casos y nunca los convierte en cero: módulo ausente (HM, HF, AUT, APT, se decide primero), denominador cero (DEN0) y datos insuficientes (INSUF). Probado en tests/test_metrics_robustness.py, incluido un dataset sin citas desde el 2025-07-01 y otro sin ninguna cita.

## Fixture calculado a mano: cinco variantes por la ruta completa

| Variante | history_mode | available + not_available | 31 ids una vez | matriz = esperada | valores por src/metrics.py = a mano | DEN0 / INSUF fuera del catálogo |
|---|---|---|---|---|---|---|
| `v_full` | full_event_history | 31 + 0 | ✓ | ✓ | 30 / 30 | DEN0 |
| `v_milestone` | milestone_first_entry | 25 + 6 | ✓ | ✓ | 25 / 25 | DEN0 |
| `v_snapshot` | snapshot_only | 16 + 15 | ✓ | ✓ | 16 / 16 | DEN0 |
| `v_no_automated` | full_event_history | 23 + 8 | ✓ | ✓ | 22 / 22 | DEN0 |
| `v_no_appointments` | full_event_history | 25 + 6 | ✓ | ✓ | 24 / 24 | DEN0 |

Cada valor disponible de cada variante se comprueba por archivos canónicos → validación → reglas del perfil → adaptador → src/metrics.py (+ history.py); el recálculo independiente de las pruebas reproduce los mismos valores. Las tasas DEN0 fuera del catálogo son las de nurture (el fixture no tiene datos de nurture) y, cuando aparece, una tasa de WhatsApp personalizado con un grupo vacío.

### Inventario y cobertura del fixture

El fixture de F2 tiene **12 registros sintéticos construidos a mano** (10 elegibles, 1 duplicado, 1 reactivación), 32 actividades, 11 citas y 27 eventos de etapa con historial completo (24 hitos de primera entrada en la variante de hitos). Es independiente del generador; `tests/fixtures/canonical_handcalc/expected.json` contiene las tablas de origen, las derivaciones y todos los valores esperados, calculados a mano. **Sustituye al borrador anterior de 9 registros (R1–R9); no es el fixture aprobado previamente**, que no pudo recuperarse de esta sesión y no se ha reconstruido. Su procedencia (fechas y citas cambiadas en v1.2.0-f2, actividades del límite de seguimiento añadidas en v1.2.1-f2) queda registrada en `expected.json`.

| Caso | Filas |
|---|---|
| manual_route | F01; F02; F03; F06; F07; F08; F09 |
| bot_route | F04; F05; F10 |
| duplicate | F11 (same person_key as F01, 2 days later) |
| reactivation | F12 (parent F05, closed_lost future_intake, same person_key) |
| no_show | AP02 (F02, rebooked as AP03); AP08 (F05, bot); AP09 (F07, rebooked as AP11) |
| reschedule | AP04 -> AP05 (F03; AP04 replaced, excluded) |
| cancellation | AP10 (F10) |
| pending_after_snapshot | AP11 (F07) |
| human_activity_before_interview | A012, A013 (F03 before AP05); A019 (F05 before AP08, bot route) |
| human_activity_after_interview | A003 (F01 +23 h); A014 (F03 +22 h); A010 (F02 +66 h) |
| followup_exactly_48h | A031 (F04: held 2025-03-12 10:00:00, call 2025-03-14 10:00:00, counted) |
| followup_48h_plus_1s | A032 (F02: held 2025-02-17 16:00:00, WhatsApp 2025-02-19 16:00:01, not counted) |
| automated_activity_inside_window_not_counted | A009 (F02 email); A017 (F04 email) |
| re_entry | F03 enters interview_held twice (E13, E15) |
| regression | E14 (F03 interview_held -> interview_booked) |
| reopen | E23 (F05 closed_lost -> opportunity) |
| weekday_and_weekend_arrivals | weekday F01 F03 F06 F08; weekend F02 F07 |
| sla_window_exclusion | F09 (created < 24 h before the snapshot) |
| immature | F08; F09 |
| amounts | F01 single payment (one-time discount); F04 instalments (no one-time discount) |
| history_modes | v_full; v_milestone; v_snapshot |
| capability_absent | v_no_automated (no is_automated); v_no_appointments (no appointments table) |

## Dataset canónico de admisiones (build/canonical/admissions, fuera del manifiesto)

| Archivo | filas | SHA-256 |
|---|---|---|
| `build/canonical/admissions/dataset.csv` | 1 | `a166bd21ce546bc6` |
| `build/canonical/admissions/records.csv` | 7945 | `06365c95d3654439` |
| `build/canonical/admissions/stage_events.csv` | 23090 | `57a8ec3c5f9cf087` |
| `build/canonical/admissions/activities.csv` | 83610 | `ffb7cda527d30ae3` |
| `build/canonical/admissions/appointments.csv` | 5816 | `e73edc56e84d7ab8` |
| `build/canonical/admissions/record_attributes.csv` | 60945 | `54a06a923492307e` |

## Archivos

**Frente a F1** (`reports/f1/MANIFEST_F1.sha256`): modified (declared): 5, new (declared): 67, unchanged: 31. Archivos de F1 modificados:

- `README.es.md` — sección F2, estructura y cómo ejecutar (ninguna cifra cambia)
- `README.md` — F2 section, repository structure and how to run (no figure changed)
- `scripts/export_metrics.py` — guard only: refuses to write reports/f1/ on the F2 tree
- `scripts/f1_run.py` — guard only: refuses to run on the F2 tree (reports/f1/ is frozen)
- `src/metrics.py` — authorised v1.2.1-f2 robustness fix (zero denominators, empty appointment structures); same 47 values

**Frente a la revisión F2 anterior** (`v1.2.2-f2`, `reports/f2/MANIFEST_F2_v1.2.2.sha256`): modified (declared): 4, new (declared): 1, unchanged: 104. Modificados:

- `docs/PROJECT_STATUS.es.md` — restricciones vigentes frente a objetivos futuros; adaptador UTC y preparación para datos reales / CRM indicados como no disponibles
- `docs/PROJECT_STATUS.md` — current restrictions vs future goals; UTC adapter and real-data / CRM readiness stated as not available
- `reports/f2/metrics_f2_canonical.json` — only the version_id field (v1.2.2-f2 -> v1.2.3-f2); all values identical
- `scripts/f2_run.py` — report template only: obsolete contract paragraph removed; v1.2.3-f2 identifiers

Nuevos:

- `reports/f2/MANIFEST_F2_v1.2.2.sha256`

Hashes por archivo: [`F1_COMPARISON.es.md`](F1_COMPARISON.es.md) · [`F2_PREV_COMPARISON.es.md`](F2_PREV_COMPARISON.es.md).
