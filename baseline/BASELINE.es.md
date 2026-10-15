**Idioma:** [English](BASELINE.md) | Español

# Línea base F0 (`v1.0.0-f0`)

F0 congela la v1 del proyecto como referencia verificable antes de cualquier refactorización (F1). No cambia el comportamiento: el generador, los datos, las comprobaciones y el análisis son los de la v1. Todos los datos y cifras son sintéticos (semilla 42).

## Qué identifica la versión congelada

| Elemento | Significado |
|---|---|
| `baseline_id` = `v1.0.0-f0` | Etiqueta legible de la versión, guardada en `metrics_v1.json` |
| **Tree id** | SHA-256 de `baseline/MANIFEST.sha256`, que lista el SHA-256 de cada archivo del repositorio (código, configuración, datos, documentación, notebook ejecutado, JSON de métricas, entorno). Cualquier cambio en cualquier archivo cambia el tree id. El valor de cada ejecución figura en `F0_REPORT.es.md` |
| Git | La carpeta no es un repositorio git y no se ha hecho ningún commit. Cuando se autoricen commits, el mismo contenido puede etiquetarse `v1.0.0-f0`; después, `python scripts/f0_baseline.py --check` confirma que el árbol etiquetado reproduce el manifiesto |

El tree id es válido para el entorno registrado en `environment.txt`. Otras versiones de las librerías pueden cambiar los bytes del notebook ejecutado aunque los datos sean idénticos.

## Archivos

| Archivo | Contenido |
|---|---|
| `metrics_v1.json` | 47 métricas con definición, unidad, población, numerador, denominador, base temporal, referencias a `docs/kpi_definitions*.md`, recuentos y valor; madurez por cohorte mensual; conciliación de anomalías; hashes de entrada; resumen de comprobaciones lógicas |
| `MANIFEST.sha256` | SHA-256 por archivo (se excluye a sí mismo y a los informes de ejecución) |
| `environment.txt` | Versiones exactas de Python y de las librerías usadas |
| `F0_REPORT.md` · `F0_REPORT.es.md` | Comandos ejecutados, códigos de salida, duraciones, resultados de las pruebas, hashes de entrada, auditoría del seguimiento (se regeneran en cada ejecución) |

Los hashes por sí solos no validan resultados. Las métricas las valida `tests/test_baseline.py`, que recalcula cada métrica de forma independiente a partir de los CSV con pandas (sin importar el código del notebook) y exige que numeradores, denominadores y valores coincidan. También comprueba que cada métrica esté descrita por completo, que las cifras principales de los README coincidan con la línea base en los dos idiomas y que una JSON alterada se rechace.

## Fuente de verdad

| Capa | Fuente de verdad | Artefacto derivado |
|---|---|---|
| Datos sintéticos | `src/generate_data.py` + `config/simulation_params.yaml` (semilla 42) | `data/*.csv` (verificados por hash) |
| Reglas de integridad | `src/checks.py` + `tests/test_integrity.py` | — |
| Cálculo de métricas (F0) | Celdas de código definidas en `scripts/build_notebook.py` | `notebooks/admissions_analysis.ipynb` (ejecutado) y `baseline/metrics_v1.json` |
| Verificación de métricas | `tests/test_baseline.py` (recálculo independiente) | — |
| Narrativa | `scripts/notebook_conclusions.md`, `README*.md`, `docs/` | — |

El notebook ejecutado es un artefacto generado: se reconstruye desde `scripts/build_notebook.py` en un kernel nuevo, quitando el contenido propio de cada ejecución (marcas de tiempo, direcciones de memoria, identificadores aleatorios de tablas y salidas troceadas), de modo que con las mismas entradas el notebook es idéntico byte a byte.

**Objetivo para F1 (no se hace en F0):** mover el cálculo de métricas a un `src/metrics.py` versionado; el notebook solo lo importaría y lo presentaría, y `metrics_v1.json` seguiría siendo la referencia de regresión.

## Cómo reproducir o verificar

```bash
python scripts/f0_baseline.py          # ejecución limpia: generar → notebook → pruebas → manifiesto → informe
python scripts/f0_baseline.py --check  # ejecución limpia y comparación con el manifiesto guardado (exit 1 si hay diferencias)
```

## Fuera del alcance de F0

Sin refactorizar el núcleo, sin esquema canónico, sin aplicación web, sin conexión a CRM y sin datos reales.
