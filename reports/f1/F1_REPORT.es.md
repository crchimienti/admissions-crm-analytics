**Idioma:** [English](F1_REPORT.md) | Español

# F1 — informe de ejecución (`v1.1.0-f1`)

Generado por `python scripts/f1_run.py --check` · 2026-10-12 20:20 CEST.
Todos los datos y cifras son sintéticos (semilla 42). Alcance: solo el perfil de admisiones; sin afirmaciones de portabilidad.

## Versión

| Elemento | Valor |
|---|---|
| Identificador F1 | `v1.1.0-f1` |
| Tree id F1 (SHA-256 de `reports/f1/MANIFEST_F1.sha256`) | `9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651` |
| Referencia | `v1.0.0-f0` · tree id F0 `eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df` |
| Git | sin commit ni tag (no es un repositorio git; no autorizado) |
| Entorno | python==3.13.16, numpy==2.5.3, pandas==3.0.5, pyyaml==6.0.3, matplotlib==3.11.2, nbformat==5.11.1, nbconvert==7.17.2, ipykernel==7.4.0, pytest==9.1.1 — idéntico a baseline/environment.txt |

## Comandos y resultados

| # | Comando | exit | segundos |
|---|---|---|---|
| 1 | `remove data/, notebooks/admissions_analysis.ipynb, reports/f1/` | 0 | 0.0 |
| 2 | `python3 src/generate_data.py` | 0 | 5.5 |
| 3 | `python3 scripts/build_notebook.py` | 0 | 27.3 |
| 4 | `python3 scripts/export_metrics.py` | 0 | 10.4 |
| 5 | `python3 -m pytest -q` | 0 | 177.3 |

| Comprobación | Resultado |
|---|---|
| Notebook (kernel nuevo) | notebook: notebooks/admissions_analysis.ipynb · code cells 18 · errors 0 |
| Pruebas | **153 passed, 0 failed** |
| 47 métricas frente a F0 | **47 / 47** coinciden (ids, orden, campos descriptivos, numeradores, denominadores, valores a 6 decimales) |
| baseline/ antes y después de la ejecución | idéntica byte a byte (7 archivos) |
| Reproducibilidad de F1 | idéntica al manifiesto F1 guardado (37 archivos) — tree id 9206c83e2b6fea80 |

## Archivos comparados con el manifiesto F0

| Estado | Archivos |
|---|---|
| modified (declared) | 5 |
| new (declared) | 7 |
| unchanged | 25 |

Detalle por archivo, con ambos hashes: [`F0_COMPARISON.es.md`](F0_COMPARISON.es.md).
