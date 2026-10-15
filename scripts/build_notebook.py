"""Build (and execute) the analysis notebook from versioned source.

Construye (y ejecuta) el notebook de análisis a partir de código versionado.

The notebook's cells are defined here; `notebooks/admissions_analysis.ipynb` is a rendered artifact.
Since F1 (v1.1.0-f1) every table and KPI is computed by `src/metrics.py`; the cells only call it, format and plot.
Usage:
    python scripts/build_notebook.py            # build + execute in a fresh kernel, strip volatile metadata
    python scripts/build_notebook.py --no-exec  # build only
"""
from __future__ import annotations

import argparse
from pathlib import Path

import nbformat as nbf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NB_PATH = ROOT / "notebooks" / "admissions_analysis.ipynb"

nb = nbf.v4.new_notebook()
C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Admissions CRM analytics — synthetic case study
# Analítica CRM de admisiones — caso con datos sintéticos

> **EN — Synthetic data.** Every row, rate and amount in this notebook is **synthetic**, generated from the
> *synthetic scenario parameters* in `config/simulation_params.yaml` (seed 42). Differences between sources,
> routes or profiles reproduce those parameters; they are not findings about any real company, team or market.
> No causal effect is programmed for any intervention, so no causal claim is made.
>
> **ES — Datos sintéticos.** Todas las filas, tasas e importes de este notebook son **sintéticos**, generados a
> partir de los *parámetros del escenario sintético* de `config/simulation_params.yaml` (semilla 42). Las
> diferencias entre fuentes, rutas o perfiles reproducen esos parámetros; no son hallazgos sobre ninguna empresa,
> equipo o mercado reales. No se programa ningún efecto causal de ninguna intervención, así que no se afirma causalidad.

Definitions / Definiciones: `docs/kpi_definitions.md` · `docs/kpi_definitions.es.md`.
""")

code(r'''
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import metrics   # single implementation of every table and KPI shown below (v1.1.0-f1)

pd.set_option("display.max_columns", 40, "display.width", 160)
ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
pop = metrics.population_counts(ctx)

# Chart style: one categorical order (validated reference palette), recessive grid, thin marks
BLUE, ORANGE, AQUA, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
                     "font.size": 9.5, "axes.titlesize": 11, "axes.titleweight": "bold", "legend.frameon": False})

# Presentation helpers only (formatting, no computation)
pct = lambda x: "—" if pd.isna(x) else f"{x:.1%}"
def fmt_rows(series, counts=(), hours=()):
    # Show a module Series as a one-column table: counts as integers, hours with 'h', everything else as %.
    sty = series.to_frame("value").style.format(pct)
    if counts:
        sty = sty.format("{:,.0f}", subset=pd.IndexSlice[list(counts), :])
    if hours:
        sty = sty.format("{:.1f} h", subset=pd.IndexSlice[list(hours), :])
    return sty
print(f"snapshot_date = {pop['snapshot']} · leads rows = {len(ctx.raw_leads):,} · activities = {len(ctx.A):,}")
''')

md("""
## 1. Data validation / Validación de datos
* **Logic checks** must have zero violations; a violation is a generator bug.
* **Deliberate anomalies:** each detection rule is compared with `data/dq_ground_truth.csv` *in the same unit*.
  `detectable` is the part of the injected cases the rule can observe at the snapshot; the check requires
  `detected = detectable` exactly. Cases that cannot be observed yet are counted in `not_detectable` and explained.
* **Comprobaciones lógicas:** deben dar cero. **Anomalías deliberadas:** cada regla se compara con la verdad de referencia en la misma unidad;
  se exige `detected = detectable` y los casos aún no observables se cuentan y se explican.
""")
code(r'''
val = metrics.validation_summary(ctx)
print(f"Logic checks: {val['logic_checks']} · checks with violations: {val['logic_checks_with_violations']}")
display(val["anomalies"].rename(columns={"check": "anomaly", "detail": "detection rule · rate"})
        .style.format({c: "{:,.0f}" for c in ["injected", "detectable", "detected", "not_detectable"]}))
gov_row = val["governance_indicator"]
print(f"Governance indicator — {gov_row.check}: {gov_row.detail}\n  {gov_row.note}")
print("Rate-drift warnings:", val["warnings"] or "none")
''')

md("""
## 2. Volume, identity and cohort maturity / Volumen, identidad y madurez
* **Eligible lead** = not a duplicate and not a reactivation. Reactivations are reported separately.
* **Mature lead** = `snapshot_date − created_at ≥ 60 × 24 h`, computed **per lead with full timestamps** (`checks.cohort_maturity`).
* The cohort label is **computed**, not declared: `mature` if 100 % of its eligible leads are mature, `partial` if some, `immature` if none.
  The table shows the newest lead of each cohort and the minimum age, so the label can be verified.
  Cohort conversions use mature leads only.
* *ES:* madurez calculada por lead con timestamps completos; la etiqueta de cada cohorte se calcula y la tabla muestra el lead más reciente y la edad mínima para verificarla.
""")
code(r'''
coh = metrics.cohort_table(ctx)
print(f"Snapshot {pop['snapshot']} − 60 × 24 h = {pop['maturity_threshold']}: leads created at or before this instant are mature.")
display(coh[["eligible_leads", "mature_leads", "mature_share", "label", "newest_lead_created_at", "min_age_days",
             "duplicates", "reactivations"]].style.format({"mature_share": pct}))
print(f"Eligible leads: {pop['eligible_leads']:,} · duplicates: {pop['duplicates']:,} · reactivations: {pop['reactivations']:,}")

fig, ax = plt.subplots(figsize=(8, 3))
ax.bar(coh.index.astype(str), coh.eligible_leads, color=BLUE, width=0.6)
ax.set_title("New eligible leads per month (synthetic)"); ax.set_ylabel("leads")
ax.grid(axis="x", visible=False); plt.tight_layout(); plt.show()
''')

md("""
## 3. Entry and SLA / Entrada y SLA
**Project analytical definition, not an official historical KPI.** Manual route: first human attempt, measured
in **calendar hours**. Bot route: pre-interview confirmation and human contact, analysed separately.
SLA denominators use manual leads created ≥ 24 h before the snapshot, so every 24-hour window is complete.

The weekday / weekend split shows observed values only. Calendar hours include nights and weekends, when the scenario's
advisors (Mon–Fri 09–19, a synthetic parameter) do not work, so leads arriving outside working hours can be penalised by
this definition. The split does not show that every weekend lead misses the target; whether the SLA should be measured
in calendar or working hours is a definition to validate.
*ES: la división entre semana / fin de semana muestra valores observados. Las horas naturales incluyen noches y fines de semana, en los que los asesores del escenario no trabajan, por lo que esta definición puede penalizar a los leads que entran fuera de horario; no demuestra que todos incumplan.*
""")
code(r'''
sla = metrics.sla_summary(ctx)
display(fmt_rows(sla, counts=["eligible leads"],
                 hours=["manual: median first response (h)", "manual: p90 first response (h)"]))
display(metrics.sla_by_arrival(ctx).style.format({"sla_24h": "{:.1%}", "median_h": "{:.1f}"}))
''')
code(r'''
# Bot route: pre-interview confirmation and human contact before the first appointment
bot = metrics.bot_pre_interview(ctx)
print(f"Bot route leads: {bot['bot_route_leads']:,}")
print(f"  with bot confirmation or reminder before first appointment: {pct(bot['confirmation_rate'])}")
print(f"  with human advisor contact before first appointment:        {pct(bot['human_contact_rate'])}")
''')

md("""
## 4. Main KPI and interview metrics / KPI principal y métricas de entrevista
* **Main KPI (lead level):** mature eligible leads with ≥1 `held` appointment / **all** mature eligible leads, both routes.
* **Per-appointment show rate (appointment level):** `held` / (`held` + `no_show`) over *eligible appointments*:
  eligible lead, not replaced by rescheduling, scheduled ≤ snapshot. Base: month of `interview_scheduled_for`.
* **Per-lead show rate (lead level):** leads with ≥1 `held` / leads with ≥1 eligible appointment `held` or `no_show`.
""")
code(r'''
kpi_all = metrics.main_kpi_by_cohort(ctx)
print("Partial cohorts are shown with the share of leads included and are NOT compared with mature cohorts.")
display(kpi_all.style.format({"main_kpi": "{:.1%}", "manual_route": "{:.1%}", "bot_route": "{:.1%}", "mature_share": "{:.1%}"}))
tot = metrics.main_kpi_totals(ctx)
display(fmt_rows(tot, counts=["mature eligible leads"]))

kpi = metrics.main_kpi_by_cohort(ctx, mature_only=True)
fig, ax = plt.subplots(figsize=(8, 3.2))
x = kpi.index.astype(str)
ax.plot(x, kpi.main_kpi, color=BLUE, lw=2, marker="o", ms=4, label="All eligible leads (main KPI)")
ax.plot(x, kpi.manual_route, color=ORANGE, lw=2, marker="o", ms=4, label="Manual route")
ax.plot(x, kpi.bot_route, color=AQUA, lw=2, marker="o", ms=4, label="Bot route")
ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.set_ylim(0, 1)
ax.set_title("Main KPI by cohort — mature cohorts only (synthetic)")
ax.legend(loc="lower left", ncols=3); plt.tight_layout(); plt.show()
''')
code(r'''
# Appointment-level metrics on eligible appointments
appt = metrics.appointment_metrics(ctx)
ex = appt["excluded"]
print("Appointments excluded from the show rate: rescheduled (replaced) =", ex["rescheduled_replaced"],
      "· pending (future) =", ex["pending_future"], "· cancelled =", ex["cancelled_eligible"], "(cancellation rate only)")
display(appt["rates"].to_frame("value").style.format("{:.1%}"))
print(f"Unit check: {appt['appointments_held_or_no_show']:,} appointments (held+no_show) vs "
      f"{appt['per_lead_denominator']:,} leads in the per-lead denominator")
''')
code(r'''
# Personal WhatsApp (from 2025-07-01): ASSOCIATION ONLY. The generator programs ZERO effect on show.
assoc = metrics.personal_whatsapp_association(ctx)
display(assoc.style.format({"show_rate": "{:.1%}", "ci_low": "{:.1%}", "ci_high": "{:.1%}"}))
print("Interpretation: any difference here is noise or mix, because the scenario programs zero effect.\n"
      "Estimating a real effect would need a controlled pilot (random assignment of the reminder).")

m = metrics.show_rate_by_month(ctx)
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(m.index.astype(str), m.values, color=BLUE, lw=2, marker="o", ms=4)
ax.axvline("2025-07", color=MUTED, lw=1, ls="--"); ax.text("2025-07", 0.92, " personal WhatsApp starts", color=MUTED, fontsize=8)
ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.set_ylim(0, 1)
ax.set_title("Per-appointment show rate by appointment month (synthetic)"); plt.tight_layout(); plt.show()
''')

code(r'''
# Robustness: the bot-route main KPI looks higher in Jul–Oct cohorts than in Jan–Jun (same months the personal
# WhatsApp starts). The generator has NO time trend and NO WhatsApp effect. Re-running other seeds shows whether
# the difference is chance. The notebook only orchestrates the experiment; the comparison is metrics.bot_route_half_comparison.
from generate_data import Generator, load_config
rows = {42: metrics.bot_route_half_comparison(ctx.raw_leads)}
cfg_s = load_config(ROOT / "config" / "simulation_params.yaml")
for seed in (1, 2, 3):
    cfg_s["seed"] = seed
    rows[seed] = metrics.bot_route_half_comparison(Generator(cfg_s).run()[0])
display(pd.DataFrame(rows).T.rename_axis("seed").style.format({"Jan–Jun": "{:.1%}", "Jul–Oct": "{:.1%}", "z": "{:+.1f}"}))
print("Seed 42 shows a sizeable gap; other seeds do not. With zero programmed effect, the gap is chance —\n"
      "a reminder that a before/after comparison cannot attribute causality.")
''')

md("""
## 5. Funnel (mature cohorts) / Funnel (cohortes maduras)
Lead-level counts of leads that reached each milestone. Directional metrics: forms / held, enrollments / held.
""")
code(r'''
fun = metrics.funnel(ctx)
display(fun.style.format({"% of eligible": "{:.1%}", "% of previous": "{:.1%}"}, na_rep="—"))
dirm = metrics.directional_rates(ctx)
display(dirm.to_frame("value").style.format("{:.1%}"))
cyc = metrics.sales_cycle(ctx)
print(f"Sales cycle (created → enrolled), days: median {cyc['median_days']:.1f} · mean {cyc['mean_days']:.1f} · n={cyc['n']}")

fig, ax = plt.subplots(figsize=(8, 3.2))
ax.barh(fun.index[::-1], fun.leads[::-1], color=BLUE, height=0.55)
for y, (v, p) in enumerate(zip(fun.leads[::-1], fun["% of eligible"][::-1])):
    ax.text(v, y, f"  {v:,} ({p:.0%})", va="center", color=INK, fontsize=8.5)
ax.set_xlim(0, fun.leads.max() * 1.25); ax.grid(axis="y", visible=False)   # axis limit only (presentation)
ax.set_title("Funnel, mature cohorts — leads reaching each milestone (synthetic)"); plt.tight_layout(); plt.show()
''')

md("""
## 6. Sources, profiles and programmes / Fuentes, perfiles y programas
Quality = downstream conversion and net price per lead, not volume. **These differences reproduce the channel and
profile modifiers in the scenario configuration**; they demonstrate the method, not real channel performance.
""")
code(r'''
fmt = {c: "{:.1%}" for c in ["held / leads", "enrolled / leads", "enrolled / held", "ILOC share"]} | {"net € per lead": "{:,.0f}"}
for by in ("channel_group", "candidate_profile", "program_alias"):
    display(metrics.segment_table(ctx, by).style.format(fmt).set_caption(f"By {by} — mature cohorts (synthetic)"))
''')

md("""
## 7. Advisors — exploratory only / Asesores — solo exploratorio
All five advisors share **the same base parameters**; the uneven *assignment weight* is a scenario parameter, not
a real distribution. Differences in workload or conversion come from chance, the assignment weight and
reassignments; **they are not attributed to individual performance.**
Workload = eligible leads by `first_owner_id` and month (duplicates excluded; reactivations shown separately).
""")
code(r'''
wl = metrics.workload(ctx)
work = wl["realised"]
print("Realised workload (eligible leads by first owner and month):")
display(work)
print("Advisor-months by band (realised):", wl["bands"])
print("Advisor-months >150 — expected before randomness:", wl["over_150_expected"], "· realised:", wl["over_150_realised"])
print("Reactivations by first owner (separate from workload):", wl["reactivations_by_first_owner"])

fig, ax = plt.subplots(figsize=(9, 2.8))
im = ax.imshow(work.values, cmap="Blues", aspect="auto", vmin=80, vmax=200)
ax.set_xticks(range(work.shape[1]), [str(c)[-2:] for c in work.columns]); ax.set_yticks(range(work.shape[0]), work.index)
for i in range(work.shape[0]):
    for j in range(work.shape[1]):
        v = work.values[i, j]
        ax.text(j, i, f"{v}{'*' if v > 150 else ''}", ha="center", va="center", fontsize=7.5, color="white" if v > 150 else INK)
ax.grid(False); ax.set_xlabel("month (2025)")
ax.set_title("Realised workload per advisor-month (* = above 150) — synthetic"); plt.tight_layout(); plt.show()
''')
code(r'''
f = {c: "{:.1%}" for c in ["held / leads", "95% CI low", "95% CI high", "enrolled / leads", "manual SLA ≤24h"]}
display(metrics.advisor_table(ctx, "first_owner_id").style.format(f).set_caption("By first owner — exploratory (synthetic)"))
display(metrics.advisor_table(ctx, "current_owner_id").style.format(f).set_caption("By current owner — exploratory (synthetic)"))
print("Advisor activities by performer (actor_id):", metrics.advisor_activity_counts(ctx))
''')

md("""
## 8. Losses and nurture / Pérdidas y nurture
""")
code(r'''
lr = metrics.lost_reasons(ctx)
display(lr["by_exit_point"])
display(lr["distribution"].to_frame("share of closed-lost with reason").style.format("{:.1%}"))

nu = metrics.nurture_summary(ctx)
print(f"Entered nurture: {nu['entered_nurture']:,} deals · with a complete 150-day window by the snapshot: {nu['complete_window']:,}")
print(f"  reactivated within the window (complete windows only): {pct(nu['reactivation_rate_complete_window'])}")
print(f"  reactivated leads that enrolled (any window): {nu['reactivated_enrolled']} of {nu['reactivated_leads']}")
print(f"  nurture emails not sent or failed: {pct(nu['email_failure_rate'])} of {nu['nurture_emails']:,}")
''')

md("""
## 9. CRM governance at the snapshot / Gobernanza CRM en la fecha de corte
Simple indicators (no weighted score in v1). Deliberate anomalies are part of the scenario.

**Manual advisor follow-up within 48 h** (project analytical definition of the operational 24–48 h alert rule, which did not
specify calendar or working hours):
* *Counts:* advisor activities with `actor_type = advisor`, `direction = outbound`, `activity_type` in {call, whatsapp} and
  `is_automated = false`. Automated or templated emails, bot messages, tasks and notes do not count.
* *Window:* calendar hours, from the first held interview (`entered_interview_held_at`, exclusive) to 48 h later (inclusive).
  Weekends are **not** excluded.
* *Denominator:* eligible leads whose first held interview is at least 48 h before the snapshot (complete window).

*ES: cuentan llamadas y WhatsApps salientes manuales del asesor; ventana de 48 horas naturales desde la primera entrevista realizada, sin excluir fines de semana; denominador: leads elegibles con la primera entrevista realizada al menos 48 h antes del corte.*
""")
code(r'''
gv = metrics.governance(ctx)
display(fmt_rows(gv["indicators"], counts=["open leads at snapshot",
                                           "follow-up 48 h — denominator (eligible, window complete)",
                                           "follow-up 48 h — numerator (≥1 manual call/WhatsApp in window)"]))
fu = gv["followup"]
print(f"Follow-up 48 h: {fu['numerator']:,} / {fu['denominator']:,} = {pct(fu['rate'])} "
      "(row-level recount: tests/test_integrity.py::test_followup_indicator_on_dataset_matches_row_level_recount).")
print(f"Leads in the denominator with manual advisor activity BEFORE the interview: "
      f"{gv['followup_leads_with_pre_interview_activity']:,} — those earlier activities are not counted.")
print("This is a result of this synthetic run: the generator plans 80 % of follow-ups within 48 calendar hours and then\n"
      "moves advisor activity to working hours (assumptions §3.9). It describes the scenario, not a team's performance.")
print("Open leads by stage:", gv["open_by_stage"])
print("Open leads that are deliberate anomalies (stalled or untouched):", gv["open_deliberate_anomalies"])
''')

md("""
## 10. Finance (synthetic pricing rule) / Finanzas (regla de precio sintética)
Single payment: (3,200 − campaign discount) × 0.85. Instalments: 3,200 − campaign discount. The campaign discount
is drawn at random (arbitrary scenario), so no campaign seasonality can be analysed. No payments or collections.
""")
code(r'''
fin = metrics.finance(ctx)
display(fin["summary"].to_frame("value").style.format("{:,.0f}"))
print("Observed ticket range in the operational context: €2,000–2,500. The synthetic rule is not calibrated to it:"
      " instalment net prices (€2,600–2,850) sit above that range by construction.")
display(fin["by_payment_type"].style.format({"avg_net": "{:,.0f}", "total_net": "{:,.0f}", "mix": "{:.1%}"}))
display(fin["price_grid"].style.format("{:,.2f}").set_caption("Net price by campaign discount and payment type (rule check)"))
''')

md("""
## 11. Baseline metrics and reconciliation with F0 / Métricas de la línea base y conciliación con F0
The 47 baseline metrics are computed by `metrics.baseline_metrics` and compared with the frozen F0 reference
`baseline/metrics_v1.json` by `metrics.reconcile` (values at the reference rounding of 6 decimals, no extra tolerance;
numerators, denominators and descriptive fields exactly equal). The notebook writes no files: the F1 metrics document
is written by `scripts/export_metrics.py` to `reports/f1/metrics_f1.json`, and `baseline/` stays frozen.
*ES: las 47 métricas las calcula `metrics.baseline_metrics` y `metrics.reconcile` las compara con la referencia congelada de F0;
el notebook no escribe archivos y `baseline/` queda congelada.*
""")
code(r'''
import json
reference = json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8"))
doc = metrics.baseline_document(ctx, "v1.1.0-f1", ROOT)
rs = metrics.reconciliation_summary(doc, reference)
rec = rs["table"]
print(f"Metrics: {rs['metrics']} · matching F0: {rs['matching']} · missing from F1: {rs['missing_from_document'] or 'none'}")
print("Cohort maturity, anomaly reconciliation, logic checks and input hashes identical to F0:", rs["other_sections_identical"])
display(rec[["value_reference", "value", "abs_diff", "numerator_reference", "numerator", "denominator_reference",
             "denominator", "descriptive_equal", "match"]])
''')

md("""
## 12. Key figures and conclusions / Cifras clave y conclusiones
""")
code(r'''
k = metrics.key_figures(ctx)
display(pd.Series({
    "Eligible leads (12 months)": f"{k['eligible_leads']:,}",
    "Mature eligible leads": f"{k['mature_eligible_leads']:,}",
    "MAIN KPI — interviews held / opportunities": pct(k["main_kpi"]),
    "  manual route / bot route": f"{pct(k['main_kpi_manual'])} / {pct(k['main_kpi_bot'])}",
    "Per-appointment show rate": pct(k["show_rate_per_appointment"]),
    "Forms / interviews held": pct(k["forms_over_held"]),
    "Enrollments / interviews held": pct(k["enrollments_over_held"]),
    "Manual first attempt ≤ 24 h": pct(k["sla_24h_manual"]),
    "Advisor-months > 150 (realised)": k["advisor_months_over_150_realised"],
    "Average net price (€)": f"{k['average_net_price']:,.0f}",
}).to_frame("synthetic value"))
''')
md((HERE / "notebook_conclusions.md").read_text(encoding="utf-8"))



def _assign_stable_ids(notebook):
    for i, cell in enumerate(notebook.cells):
        cell["id"] = f"cell-{i:02d}"


def strip_volatile(notebook):
    """Remove run-specific content so identical runs give byte-identical files:
    execution timestamps, split stdout chunks, memory addresses in object reprs, and the random ids pandas Styler
    gives each HTML table (T_xxxxx)."""
    import re
    for ci, cell in enumerate(notebook.cells):
        cell.metadata.pop("execution", None)
        if cell.get("outputs"):   # stdout may arrive split into several chunks depending on flush timing
            merged = []
            for out in cell.outputs:
                if (out.get("output_type") == "stream" and merged and merged[-1].get("output_type") == "stream"
                        and merged[-1].get("name") == out.get("name")):
                    merged[-1]["text"] = "".join(merged[-1]["text"]) + "".join(out["text"])
                else:
                    merged.append(out)
            cell.outputs = merged
        for k, out in enumerate(cell.get("outputs", [])):
            plain = out.get("data", {}).get("text/plain")
            if plain is not None:   # object reprs carry memory addresses (e.g. "<Styler at 0x7f...>")
                ptxt = "".join(plain) if isinstance(plain, list) else plain
                out["data"]["text/plain"] = re.sub(r" at 0x[0-9a-f]+>", ">", ptxt)
            html = out.get("data", {}).get("text/html")
            if html is None:
                continue
            text = "".join(html) if isinstance(html, list) else html
            ids = list(dict.fromkeys(re.findall(r"T_[0-9a-f]{5}", text)))
            for j, uid in enumerate(ids):
                text = text.replace(uid, f"T_c{ci:02d}o{k}t{j}")
            out["data"]["text/html"] = text
    notebook.metadata.pop("widgets", None)
    return notebook


def build():
    nb.cells = C
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    _assign_stable_ids(nb)
    return nb


def execute(notebook, timeout=900):
    from nbconvert.preprocessors import ExecutePreprocessor
    import notebook_rendering                       # v1.4.1-gh: reference chart rendering fixed by the project
    notebook_rendering.check_files()               # missing or changed font file: stop here, never fall back
    ep = ExecutePreprocessor(timeout=timeout, kernel_name="python3",   # always a new kernel
                             extra_arguments=[f"--IPKernelApp.exec_lines={notebook_rendering.kernel_exec_line()}"])
    try:
        ep.preprocess(notebook, {"metadata": {"path": str(NB_PATH.parent)}})
    except RuntimeError as exc:
        if "Kernel died" in str(exc):   # notebook_rendering stops the kernel when the reference rendering fails
            raise SystemExit("the notebook kernel stopped at start-up: the reference chart rendering could not be "
                             "applied (scripts/notebook_rendering.py); no other font is used") from exc
        raise
    notebook.metadata["language_info"] = {"name": "python"}
    return strip_volatile(notebook)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-exec", action="store_true")
    args = ap.parse_args()
    notebook = build()
    if not args.no_exec:
        notebook = execute(notebook)
    with open(NB_PATH, "w", encoding="utf-8", newline="\n") as fh:   # same bytes on every OS (v1.4.0-gh)
        nbf.write(notebook, fh)
    errors = sum(o.get("output_type") == "error" for c in notebook.cells for o in c.get("outputs", []))
    n_code = sum(c.cell_type == "code" for c in notebook.cells)
    print(f"notebook: {NB_PATH.relative_to(ROOT)} · code cells {n_code} · errors {errors}")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
