**Idioma:** [English](F0_REPORT.md) | Español

# Línea base F0 — informe de ejecución

Generado por `python scripts/f0_baseline.py --check` · 2026-10-12 19:32 CEST.
Todos los datos y cifras son sintéticos (semilla 42).

## Versión congelada

| Elemento | Valor |
|---|---|
| Identificador | `v1.0.0-f0` |
| Tree id (SHA-256 de `baseline/MANIFEST.sha256`) | `eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df` |
| Commit / tag de git | ninguno — la carpeta no es un repositorio git y no se ha hecho ningún commit (según lo indicado) |
| Entorno | python==3.13.16, numpy==2.5.3, pandas==3.0.5, pyyaml==6.0.3, matplotlib==3.11.2, nbformat==5.11.1, nbconvert==7.17.2, ipykernel==7.4.0, pytest==9.1.1 |

## Comandos y resultados

| # | Comando | exit | segundos |
|---|---|---|---|
| 1 | `remove data/, notebooks/admissions_analysis.ipynb, baseline/metrics_v1.json` | 0 | 0.0 |
| 2 | `/usr/bin/python3 src/generate_data.py` | 0 | 5.2 |
| 3 | `/usr/bin/python3 scripts/build_notebook.py` | 0 | 26.2 |
| 4 | `/usr/bin/python3 -m pytest -q` | 0 | 138.4 |

| Comprobación | Resultado |
|---|---|
| Generador | leads: 7,945  activities: 89,426  dq_ground_truth: 1,943  |
| Notebook (kernel nuevo) | notebook: notebooks/admissions_analysis.ipynb · code cells 18 · errors 0 |
| Pruebas | **96 passed, 0 failed** |
| Comprobaciones lógicas | 71 · violaciones 0 |
| Métricas de la línea base | 47 métricas, cada una recalculada de forma independiente a partir de los CSV por `tests/test_baseline.py` |
| Comprobación de reproducibilidad | idéntica al manifiesto guardado (27 archivos) — tree id eb4f60681f71e88a |

## Hashes de entrada (SHA-256)

| Archivo | SHA-256 |
|---|---|
| `config/simulation_params.yaml` | `51c5d18fb1c7b3221dc06d0764413353ccaaee7f1cfff6851c880b622653708f` |
| `data/leads.csv` | `255720913fea99f247e657e0969597c2d4652fb1f09e5bec3e61ea566cd22a0b` |
| `data/activities.csv` | `3318a0b81877ae8b63f916cda6b459723e508f59b5a27b70ab87de9df5b4b25e` |
| `data/dq_ground_truth.csv` | `f0dc4ac66ddc789d5a37ae3b07e36439dd581d34ea36f0f3b4131893f0699a7b` |

El resto de archivos del repositorio figura en `baseline/MANIFEST.sha256`.

## Auditoría del seguimiento postentrevista

| Elemento | Valor |
|---|---|
| Leads elegibles con entrevista realizada | 3.431 |
| Excluidos: ventana de 48 h no completa en el corte | 28 |
| Denominador | 3.403 |
| Numerador (≥1 llamada/WhatsApp manual del asesor con held < activity_at ≤ held + 48 h) | 2.118 |
| Indicador | **62,2 %** |
| Actividades del asesor de esos leads: en ventana / en el instante de la entrevista / antes / después de 48 h | 2.423 / 0 / 5.743 / 2.421 |
| Contraste: regla incorrecta 'primera actividad del lead en 48 h' | 3.082 leads (no se usa) |
