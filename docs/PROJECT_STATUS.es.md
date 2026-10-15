**Idioma:** [English](PROJECT_STATUS.md) | Español

# Estado del proyecto (preparación para GitHub, `v1.4.4-gh`)

> **Uso:** este documento es la referencia al retomar una sesión. Si una especificación no aparece aquí ni en los archivos que se citan, **no se sustituye ni se reconstruye**: se pide a la responsable del proyecto. Cualquier cambio de este documento debe reflejar una decisión aprobada.

## 1. Restricciones y objetivos

### 1.1 Principios del proyecto (sin fecha de caducidad)

- No se mencionan ni se intenta identificar empresas, marcas, programas, alumnos, asesores ni clientes.
- Los resultados sintéticos no se presentan como históricos reales. No se afirma causalidad a partir de datos simulados.
- Documentación bilingüe EN/ES. Se separan contexto real anonimizado, decisiones analíticas, parámetros sintéticos y resultados sintéticos.
- Cada fase se implementa solo tras aprobación explícita, y se detiene al terminar.

### 1.2 Restricciones vigentes hasta nueva autorización

Estas restricciones no son prohibiciones permanentes: rigen hasta que la responsable autorice expresamente lo contrario en una fase concreta.

- Solo datos sintéticos, creados desde cero. No se usan ni se solicitan datos reales, exports, capturas, nombres, emails, teléfonos ni identificadores.
- Sin conexión a HubSpot ni a ningún otro CRM.
- Sin app web (Streamlit u otra).
- Sin repositorio Git, commits, tags ni publicación en GitHub. La preparación para GitHub (`v1.4.0-gh`) es solo local.
- No se generaliza todavía el generador sintético ni se afirma portabilidad a otros funnels.

### 1.3 Objetivos futuros (todavía no autorizados)

Figuran en la evolución prevista del proyecto, pero ninguno está autorizado ni empezado. Cada uno requerirá su propio plan y aprobación:

- MVP de app web que funcione con CSV y datos sintéticos, sin credenciales ni CRM real.
- Integración con HubSpot solo de lectura, como fase separada.
- Publicación del repositorio en GitHub.
- Prueba con un segundo funnel genérico antes de cualquier afirmación de portabilidad.

## 2. Versiones congeladas

| Versión | Contenido | Identificador | Dónde |
|---|---|---|---|
| `v1.0.0-f0` | línea base F0 (47 métricas) | tree id `eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df` (SHA-256 de `baseline/MANIFEST.sha256`) | `baseline/`, `admissions-crm-analytics-v1.0.0-f0.zip` |
| `v1.1.0-f1` | `src/metrics.py` como fuente única | tree id `9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651` | `reports/f1/`, `admissions-crm-analytics-v1.1.0-f1.zip` |
| `v1.2.0-f2` | contrato canónico, mapeo, adaptador, fixture | tree id `2ba1a33f9001b613ed75192eee11c6c7c591c3cb321e51c07cb995b375eddc1e` | `reports/f2/MANIFEST_F2_v1.2.0.sha256`, ZIP v1.2.0-f2 |
| `v1.2.1-f2` | corrección de robustez de `metrics.py`, fixture oficial | tree id `f71ca2471525fbaa28b3b2a29f1012f5c9a18671a2f57c178de97a15788a95e4` | `reports/f2/MANIFEST_F2_v1.2.1.sha256`, ZIP v1.2.1-f2 |
| `v1.2.2-f2` | contrato 0.1.1 (`seq`), orden de eventos, documentación del contrato — aprobada como versión de trabajo de F2 | tree id `ddfc93cf87313a3b22d4a59961d938c420fcd97d15c8b530b0947457d9afc1a9` | `reports/f2/MANIFEST_F2_v1.2.2.sha256`, ZIP v1.2.2-f2 |
| `v1.2.3-f2` | solo corrección de documentación de v1.2.2-f2 — **cierre de F2, congelado** | tree id `a1df9fca9a38538f912fadfb437b4831f609962baa7b97fe763f68ec7a0885db` | `reports/f2/`, ZIP v1.2.3-f2 |
| `v1.3.0-f3` | F3.0: especificación declarativa de 8 KPIs y motor en paralelo con `metrics.py` | tree id `b189d44e9d092d3481817a28e7fcca98535cf311286affa079bf5af1d560e1bd` | `reports/f3/MANIFEST_F3_v1.3.0.sha256`, ZIP v1.3.0-f3 |
| `v1.3.1-f3` | correcciones de F3.0 frente a la especificación de aprobación: el motor ya no carga `metrics.py` ni siquiera indirectamente, HF en campos de etapa, APT+FLD combinados, equivalencia de elegibilidad en las cinco variantes, pruebas y texto de F3.5 — **cierre de F3.0, congelada** (aprobada el 2026-10-14) | tree id `f1a73209cfaf24d3768784e121f376e1d0ec485eca31ddd22f2b57e09ef23c34` | `reports/f3/`, ZIP v1.3.1-f3 |
| `v1.4.0-gh` | preparación para GitHub (solo local): README para visitantes, entorno fijado, corrección de saltos de línea, inicio rápido, gráficos, decisiones analíticas, reproducción completa, workflow de CI (sin ejecutar) | tree id `e1c13bfa5390ed5128970700941e63887ed999f6304cc1b96e946b0479b4a41d` | `reports/release/MANIFEST_RELEASE_v1.4.0.sha256`, ZIP v1.4.0-gh |
| `v1.4.1-gh` | revisión acotada de v1.4.0-gh (solo local): renderizado de gráficos de referencia fijado por el proyecto (fuentes Inter incluidas, OFL 1.1), comparación de rutas de Windows en `test_reports_f2_frozen`, bloque de resultados y redacción del README | tree id `a2e68371cadd318a0d2d72d33d55663ab68d41dea2d7706253cbcbb927d9c7bb` | `reports/release/MANIFEST_RELEASE_v1.4.1.sha256`, ZIP v1.4.1-gh |
| `v1.4.2-gh` | corrección autorizada de compatibilidad detectada en Windows: el CSV temporal de `test_regeneration_is_reproducible` se escribe con LF | tree id `98841cc859eec50fb11a2772263dbc1595f16ce4a86952584729791e1c8096c2` | `reports/release/MANIFEST_RELEASE_v1.4.2.sha256`, ZIP v1.4.2-gh |
| `v1.4.3-gh` | niveles de verificación separados: analítica portable (`--mode portable`) y gráfica estricta (por defecto); firma estructural de los gráficos; trabajos de CI separados | tree id `a9da920c3e2e8a3b7ee6fed8fff5875faf25fd2b05ebe840c859e3841c232d7b` | `reports/release/MANIFEST_RELEASE_v1.4.3.sha256`, ZIP v1.4.3-gh |
| `v1.4.4-gh` | licencias (MIT para el código, CC BY 4.0 para el contenido, fuentes Inter con SIL OFL 1.1) y documentación del resultado de Windows; sin cambios en código, datos, notebook, gráficos ni fuentes — versión local final antes del primer commit | tree id = SHA-256 de `reports/release/MANIFEST_RELEASE.sha256` (figura en `reports/release/RELEASE_REPORT.es.md`) | `reports/release/`, ZIP v1.4.4-gh |

`baseline/`, `reports/f1/`, `reports/f2/` y `reports/f3/` no se escriben nunca. `scripts/f0_baseline.py`, `scripts/f1_run.py`, `scripts/export_metrics.py`, `scripts/f2_run.py` y `scripts/f3_run.py` se niegan a ejecutarse en el árbol actual. F0, F1, F2 y F3 se verifican desde sus ZIP en una carpeta limpia. El árbol actual se verifica con `python scripts/release_run.py --check`, que lo compara en solo lectura con `reports/f3/MANIFEST_F3.sha256` y solo escribe `reports/release/`.

## 3. Modificaciones autorizadas de archivos de fases congeladas

- `src/metrics.py` (F1): corrección de robustez de v1.2.1-f2 (denominadores cero, estructuras de citas vacías). No cambia ninguna definición ni ninguno de los 47 valores. Su hash queda fijado en `tests/test_regression_f1.py`.
- `scripts/f1_run.py` y `scripts/export_metrics.py`: solo la salvaguarda que impide escribir en `reports/f1/`.
- `README.md` y `README.es.md`: secciones de F2 y F3.0, sin cambiar ninguna cifra.
- `scripts/f2_run.py` (F2): solo la salvaguarda de F3.0 que impide reescribir `reports/f2/`.
- `src/canonical/adapters/admissions.py` (F2): en F3.0, `first_human_attempt` se extrae como función reutilizable del perfil, con los mismos resultados.
- **v1.4.0-gh** (aprobada el 2026-10-14):
  - `src/generate_data.py` (F0) y `scripts/build_notebook.py` (F1): solo la corrección de saltos de línea (`lineterminator="\n"` en las tres escrituras de CSV; el notebook se escribe a través de un archivo abierto con `newline="\n"`). Los bytes producidos en Linux no cambian; con un separador de línea de Windows simulado, los bytes de los CSV ahora son iguales a F0.
  - `.gitignore`: reglas para entornos virtuales, secretos, copias locales, editores y `build/`; se conservan las cuatro reglas originales.
  - `scripts/f3_run.py` (F3): solo la salvaguarda que impide reescribir `reports/f3/`.
  - `tests/test_regression_f0.py`, `test_regression_f1.py`, `test_regression_f2.py`: reconocen estos cambios; los archivos de código quedan fijados a sus nuevos hashes (`tests/release_declared.py`).
  - `README(.es).md` reescrito para visitantes; `docs/PROJECT_STATUS(.es).md` actualizado.
- **v1.4.1-gh** (aprobada el 2026-10-14, revisión acotada):
  - `scripts/build_notebook.py` (F1): el renderizado de referencia se aplica en el kernel antes de la primera celda mediante `scripts/notebook_rendering.py` y las fuentes de `assets/fonts/inter/`; las celdas no cambian y el notebook reconstruido es idéntico byte a byte a F1 en Linux. Nuevo hash fijado en `tests/release_declared.py`.
  - `tests/test_regression_f2.py`: `test_reports_f2_frozen` compara rutas relativas POSIX (mismos hashes fijados); se añade una prueba focalizada de separadores.
  - El manifiesto de v1.4.0-gh se conserva como `reports/release/MANIFEST_RELEASE_v1.4.0.sha256` y se compara en solo lectura.
  - Detalles del renderizado: primero se aplican los valores por defecto de matplotlib (no se lee ningún `matplotlibrc` del usuario ni del sistema); si el kernel no puede aplicar el renderizado, la construcción se detiene con un mensaje explícito. `assets/fonts/inter/OFL.txt` es el archivo de licencia original de Inter v4.0, sin cambios. El trabajo manual de reproducción del workflow se ejecuta en Linux, Windows y macOS.
- **v1.4.2-gh** (aprobada el 2026-10-14, corrección autorizada de compatibilidad): `tests/test_integrity.py` (F0) — en `test_regeneration_is_reproducible` el CSV temporal se escribe con `lineterminator="\n"`, igual que el generador; la comparación byte a byte con `data/` no cambia y no se excluye nada en Windows. La detectó la responsable del proyecto en Windows con v1.4.1-gh (451 correctas, 1 fallida). El nuevo hash queda fijado en `tests/release_declared.py`, así que solo se reconoce este cambio; `tests/test_serialization.py` comprueba ahora todas las llamadas a `to_csv` de las pruebas. Ninguna otra escritura temporal de las pruebas tenía el mismo problema (las demás escriben bytes o ya fijan el salto de línea).
- **v1.4.3-gh** (aprobada el 2026-10-14, solo corrección de la validación): dos niveles de verificación, siempre informados por separado. **Analítica portable** (`python scripts/release_run.py --mode portable`): bytes de los CSV = F0; las 47 métricas y los 8 KPIs; cada celda, texto, tabla, cifra, contador de ejecución y metadato del notebook idénticos a F1, sin ningún campo volátil exento (solo pueden diferir los datos PNG); ejecución sin errores; estructura de los gráficos (datos, títulos, etiquetas de ejes, leyendas, anotaciones) idéntica a `tests/chart_signature_reference.json`, calculada por `scripts/chart_signature.py` con independencia del renderizado y comparada exactamente (sin tolerancia visual); pruebas, documentos, referencias congeladas y manifiesto guardado. Las diferencias de PNG van a una sección aparte con los hashes de ambos notebooks, el tamaño de las imágenes y los entornos de renderizado; el informe portable se escribe en `build/portable/` (ignorado por Git, fuera de todos los manifiestos de referencia); el notebook y los gráficos versionados se restauran y nunca se sobrescriben; nunca se escribe `reports/release/`. **Gráfica estricta** (por defecto, `--check`): además, el notebook debe ser idéntico byte a byte a F1, incluidas las imágenes PNG; si no, falla. F1 y todas las referencias no cambian. CI: `reproduction-portable` (Linux, Windows, macOS) y `reproduction-strict` (Linux) son trabajos separados.
- **v1.4.4-gh** (aprobada el 2026-10-15, solo licencias y documentación):
  - Licencias decididas por la responsable del proyecto: titular **Carlos Eduardo Rodriguez Chimienti**, año 2026. MIT para el código fuente original y la configuración, incluidas las celdas de código del notebook (`LICENSE`, texto oficial de MIT). CC BY 4.0 para la documentación, los gráficos originales, los datos sintéticos, los informes y las celdas narrativas, gráficos y salidas del notebook, en la medida en que existan derechos (`LICENSE-CONTENT`, con alcance y atribución). Las fuentes Inter y todos los materiales de terceros conservan sus licencias y avisos (`assets/fonts/inter/OFL.txt` sin cambios). No se reclaman derechos exclusivos sobre material no protegido. Atribución sugerida: *Carlos Eduardo Rodriguez Chimienti — Admissions CRM Analytics*; la URL del repositorio se añadirá cuando exista.
  - Decisiones del 2026-10-15: la diferencia de PNG entre Windows y Linux se acepta como limitación del renderizado estricto entre plataformas; no se harán más cambios de fuentes, hinting, renderizado ni referencias para forzarla; Windows se describe como verificado solo para el alcance analítico portable; macOS sigue sin verificar; JupyterLab (visualización interactiva) es opcional, no está instalado en el entorno de la responsable y no es un fallo de la ejecución del notebook; no se añade ningún paquete por ese motivo.

## 4. Contrato vigente: `crm-canonical/0.1.1`

- Archivo: `schema/canonical_v0.1.1.yaml`. `schema/canonical_v0.1.yaml` se conserva sin cambios. Los datasets 0.1 siguen siendo válidos; solo los 0.1.1 pueden llevar `stage_events.seq`.
- Tablas: `dataset`, `records`, `stage_events` (opcional), `activities`, `appointments` (opcional, capacidad) y `record_attributes` (prefijo `adm_`).
- `history_mode`: `full_event_history`, `milestone_first_entry` o `snapshot_only`. Nunca se deduce historial de `current_stage`, citas ni actividades.
- Timestamps: `naive_wall_clock` solo para datos sintéticos o legacy (Europe/Madrid como metadato). `utc` para el resto, con error en horas ambiguas o inexistentes. El adaptador de admisiones solo acepta `naive_wall_clock` en F2.
- Orden de eventos: `seq` si la fuente lo da; si no, `occurred_at`. Con empates sin `seq`, el orden es indeterminado y no se inventa. Solo `time_in_stage` depende del orden y entonces se informa como `ORD`.
- Diferencias con el plan aprobado (`is_duplicate` → `record_origin`, `status` → `current_status` + resultado derivado de `current_stage`, `closed_at` → `won_at`/`lost_at`, correspondencia de `stage_events`, `exited_at` y `changed_by_type` no representados): `docs/canonical_schema.es.md` §11.
- Especificación aprobada de `stage_events` (aportada por la responsable el 2026-10-13): clave (`record_id`, `seq`); obligatorios `record_id`, `seq`, `stage`, `entered_at`, `event_kind`; opcionales `exited_at`, `changed_by_type`; `seq` ordena los empates.
- Reglas neutrales C01–C09 (contrato); reglas del perfil P01–P10 (`profiles/admissions/rules.yaml`). La regla del padre de una reactivación pertenece al perfil, no al contrato.

## 5. Disponibilidad de KPIs

- Catálogo de 31 indicadores: 24 métricas y 7 de historial. `time_in_stage` es una capacidad sin valor esperado en el fixture.
- Motivos de no disponibilidad:
  - módulo ausente: `HM` (sin hitos), `HF` (sin historial completo), `AUT` (sin `is_automated`), `APT` (sin citas);
  - calculados: `DEN0` (denominador cero), `INSUF` (sin observaciones), `ORD` (orden indeterminado);
  - campo no proporcionado: `FLD` (aprobado en F3.0): la carga o el perfil no proporcionan un campo o atributo requerido; `missing` lista los campos exactos. Se combina con los demás (por ejemplo, `FLD+AUT`).
- Un KPI `not_available` lleva solo `id`, `status`, `reason` y `missing`; nunca valor, numerador ni denominador. Un cero real sigue siendo un 0 disponible.
- Matriz del fixture (disponibles + no disponibles): `v_full` 31+0, `v_milestone` 25+6, `v_snapshot` 16+15, `v_no_automated` 23+8, `v_no_appointments` 25+6. El dataset de admisiones generado se comporta como `v_milestone`.

## 6. Fixtures oficiales

- `tests/fixtures/canonical_handcalc/`: **12 registros construidos a mano**, corte **2025-07-31 23:59:00**, cinco variantes. `expected.json` contiene las tablas de origen, las derivaciones, todos los valores esperados, el inventario de cobertura y la procedencia.
  - Valores aceptados el 2026-10-13, entre otros: `contact_rate` = 7/8, `followup_48h_manual_advisor` = 3/4, retrocesos 1/25, reaperturas 1/4.
  - Sustituye al borrador anterior de 9 registros (R1–R9, corte 2025-03-31), que **no es recuperable y no debe reconstruirse**.
  - No se vuelve al fixture antiguo ni se cambia el corte a junio.
- `tests/fixtures/mapping_errors/`: un par de CSV válido y 21 casos de error.
- `tests/fixtures/timezones/`: casos de cambio de hora en Europe/Madrid.

## 7. Decisiones aprobadas por fase (resumen)

- **v1:** cuatro dimensiones independientes (`pipeline_stage`, `interview_outcome`, `lead_status`, `lost_reason`); el no-show se queda en Interview Booked.
  - KPI principal: leads elegibles maduros con al menos una entrevista realizada / todos los leads elegibles maduros, de ambas rutas.
  - Madurez: 60 × 24 h por lead.
  - ILOC en días hábiles; SLA y seguimiento en horas naturales; seguimiento manual en (realizada, realizada + 48 h].
  - Anomalías conciliadas en la misma unidad que la verdad de referencia.
- **F0:** línea base congelada de 47 métricas, con hashes SHA-256.
- **F1:** `src/metrics.py` como fuente única; el notebook solo presenta resultados; 47/47 iguales a F0.
- **F2:** contrato canónico, mapeo CSV → canónico, adaptador al `Context` de `metrics.py` y disponibilidad explícita; arquitectura CSV → canónico → `adapters/admissions` → `metrics.py`.
  - v1.2.1: corrección de robustez autorizada; fixture de 12 registros oficial.
  - v1.2.2: `seq` opcional y orden de eventos.
- **F3.0 (aprobada el 2026-10-13):** especificación declarativa `kpi-spec/0.1` (`schema/kpi_spec_v0.1.yaml`, `profiles/admissions/kpis.yaml`, `docs/kpi_spec.es.md`).
  - Motor en paralelo: `src/metrics.py` sigue siendo la referencia oficial y no se modifica.
  - Solo ocho KPIs: `eligible_leads`, `share_manual_route`, `main_kpi_interviews_held_over_opportunities`, `show_rate_per_appointment`, `forms_over_interviews_held`, `sla_first_attempt_24h_manual_weekend`, `first_response_p90_hours`, `sales_cycle_median_days`.
  - Lenguaje cerrado: cinco operaciones (`count`, `share`, `ratio`, `duration_stat`, `field_stat`), filtros solo con Y, sin expresiones, OR ni código.
  - Ningún campo se da por disponible; motivo `FLD`.
  - Ratios con la misma unidad y `relation` obligatoria (`subset_of`, `same_base`, `independent_allowed`).
  - Elegibilidad: `record_origin = original` ⇔ `is_duplicate = false` e `is_reactivation = false` es una regla del perfil de admisiones, probada con los datos generados, el camino canónico (CSV → canónico → adaptador), el fixture de 12 registros y las cinco variantes del fixture; un origen desconocido, nulo o ausente nunca entra en `eligible` sin avisar.

- **Preparación para GitHub `v1.4.0-gh` (aprobada el 2026-10-14):**
  - Se versionan: los tres CSV sintéticos, los fixtures, el notebook ejecutado y todas las referencias, informes y manifiestos que necesitan las pruebas. No se versionan: copias ZIP locales, diffs, cachés, entornos virtuales, secretos ni `build/`.
  - `.gitattributes` con `* -text`: sin conversión de fin de línea, así que un checkout en cualquier sistema recibe los bytes versionados.
  - `requirements-lock.txt` fija el entorno completo (sus ocho paquetes de referencia son los de `baseline/environment.txt`; las dependencias de una sola plataforma llevan marcadores); `requirements.txt` no cambia. Las dependencias de la app quedan separadas y todavía no se añaden.
  - `scripts/show_results.py` es de solo lectura; `scripts/export_figures.py` extrae tres gráficos del notebook ejecutado sin recalcular; `scripts/release_run.py` es la reproducción completa del árbol actual.
  - Identificadores: `v1.4.0-gh` para esta preparación; `v1.5.0-app` reservado para la demo local. Se mantienen los identificadores anteriores; sin commits ni tags retroactivos.
  - Los filtros que recalculan KPIs quedan fuera de la primera demo; sin rutas analíticas nuevas en esta preparación.
  - Windows y macOS figuran como "preparados, pendientes de verificar" hasta que el workflow de CI se ejecute allí.

## 8. Pendientes

- **F2 cerrada y congelada** en `v1.2.3-f2`.
- **F3.0 cerrada y congelada** en `v1.3.1-f3` (aprobada el 2026-10-14).
- **`v1.4.4-gh` entregada** (licencias y documentación sobre `v1.4.3-gh`), pendiente de revisión por la responsable antes del primer commit.
  - **Licencia — decidida el 2026-10-15** (ver §3, v1.4.4-gh): `LICENSE` (MIT) y `LICENSE-CONTENT` (CC BY 4.0).
  - **Renderizado de los gráficos del notebook — resuelto en v1.4.1-gh en Linux.** `scripts/build_notebook.py` aplica el renderizado de referencia dentro del kernel antes de la primera celda (`scripts/notebook_rendering.py`): los dos archivos Inter 4.000 incluidos en `assets/fonts/inter/` (SIL OFL 1.1; hashes y procedencia en `FONTS.md`), `font.family = Inter, sans-serif, DejaVu Sans` y `text.hinting = no_hinting`; cualquier otra fuente llamada Inter se ignora y un archivo ausente o cambiado detiene la construcción. Verificado en Linux sin fuente Inter del sistema ni configuración externa: el notebook reconstruido es idéntico byte a byte a F1. Windows: las imágenes PNG difieren (limitación aceptada, ver abajo); macOS: sin verificar.
  - **Comparación de rutas en Windows — corregida en v1.4.1-gh.** `test_reports_f2_frozen` compara rutas relativas POSIX, como en los manifiestos (mismos hashes fijados); una prueba focalizada cubre separadores de Windows y POSIX con rutas puras. No sustituye a ejecutar la batería en Windows.
  - **Windows 11 AMD64 — verificación analítica portable aprobada** (ejecutada por la responsable con v1.4.3-gh el 2026-10-15 a las 08:32, PowerShell, Python 3.13.16, entorno fijado idéntico a `baseline/environment.txt`): 477 pruebas correctas (0 fallidas, xfail ni xpass); 8/8 KPIs declarativos; firmas de los 5 gráficos idénticas a la referencia (datos, títulos, etiquetas, leyendas); todos los comandos del informe portable con código de salida 0; notebook y gráficos versionados sin sobrescribir. Entorno de renderizado informado: matplotlib 3.11.2, FreeType 2.14.3 (compilación local), numpy 2.5.3, Pillow 12.3.0, fuentes Inter del proyecto con los hashes registrados — las mismas versiones que la referencia Linux. **Verificación gráfica estricta no aprobada**: las imágenes PNG difieren; la causa no está determinada ni se atribuye a ninguna librería; aceptado como limitación. Antes (v1.4.2-gh): instalación, inicio rápido, regeneración de los CSV y 453 pruebas verificados. v1.4.4-gh no se ha ejecutado en Windows.
  - **Linux:** niveles analítico y gráfico estricto probados por quien preparó las entregas (sin cambios).
  - **macOS:** sin verificar.
  - **JupyterLab:** visualización interactiva opcional; no forma parte del entorno fijado.
  - **Siguiente paso (de la responsable, cuando lo autorice):** crear el repositorio, hacer un único primer commit de `v1.4.4-gh` y etiquetarlo; sin commits ni etiquetas retroactivos; después, añadir la URL del repositorio a la atribución.
- **Demo local `v1.5.0-app` planificada, no autorizada.** Requisitos registrados para su plan:
  - sin conexiones externas, CRM ni telemetría; solo comunicación local navegador–servidor;
  - puede haber cachés, pero los datos, el código y las referencias versionadas deben quedar intactos;
  - solo funciones y vistas que existen y están probadas; no se promete un filtro de cohortes maduras como parámetro existente sin verificar su API;
  - nunca se ejecutan el generador ni las pruebas al abrir la app o al interactuar con ella;
  - sin carga de CSV arbitrarios, sin edición de YAML y sin despliegue público.
- **F3.1 no autorizada:** los 27 KPIs parametrizables restantes, sin operaciones nuevas.
- **F3.5 decidida y todavía no autorizada** (soporte UTC y reglas de calendario local): una fase pequeña e independiente, después de F3.0 y antes de cualquier F4, dato real o conector CRM. Su diseño queda registrado aquí y necesita aprobación explícita propia. Hará lo siguiente:
  - almacenar y calcular duraciones sobre instantes UTC;
  - evaluar el día de la semana, `same_calendar_date`, el horario laboral y las reglas de calendario en `source_timezone`;
  - incluir fixtures de cambio de hora (DST);
  - demostrar que una duración de 24 horas y un día natural local no son siempre equivalentes;
  - mantener la regresión contra el caso sintético `naive_wall_clock`.

  F3.0 no contiene código UTC.
- **F4 no definida ni empezada.** Requiere un plan y aprobación explícita.
- **Objetivos futuros no autorizados:** ver §1.3.
- **Columnas de la especificación de `stage_events` no implementadas** (`exited_at`, `changed_by_type`): solo se añadirían con aprobación y versionando el contrato.
- **Adaptador con `timestamp_mode = utc`: no soportado.** El contrato y el mapeo aceptan y validan timestamps UTC, pero el adaptador de admisiones rechaza esos datasets (`A_TIMESTAMP_MODE`).
- **No hay preparación para datos reales ni conexión CRM funcional.** Todo lo probado usa datos sintéticos y archivos CSV locales. No existe ningún conector, credencial ni flujo de lectura de un CRM, y el proyecto no se ha probado con datos reales.
