"""Data layer of the local demo (v1.5.0-app): reads what the project already computes; adds no formula.

Capa de datos de la demo local: lee lo que el proyecto ya calcula; no añade ninguna fórmula.

Everything comes from existing, tested code and versioned files, computed in memory from data/:
  * the eight declarative KPIs and the 47 reference metrics: scripts/release_checks.load_results()
    (src/kpispec and src/metrics.py), formatted with release_checks.fmt_value / fmt_base;
  * funnel and cohort maturity: src/metrics.funnel() and cohort_table();
  * charts: the PNG outputs of the versioned executed notebook (the same images as docs/img/), not redrawn;
  * definitions and limits: docs/analytical_decisions(.es).md.
Nothing here writes a file, runs the generator, the tests or the release run, or opens a network connection.
This module does not import streamlit, so it can be tested in the pinned analytical environment.
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / "src", ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import metrics  # noqa: E402
import release_checks as rc  # noqa: E402

NOTEBOOK = ROOT / "notebooks" / "admissions_analysis.ipynb"
REPO_URL = "https://github.com/crchimienti/admissions-crm-analytics/"

# Spanish captions for the notebook chart titles (the images themselves keep their English titles)
CHART_TITLES_ES = {
    "New eligible leads per month (synthetic)": "Nuevos leads elegibles por mes (sintético)",
    "Main KPI by cohort — mature cohorts only (synthetic)": "KPI principal por cohorte — solo cohortes maduras (sintético)",
    "Per-appointment show rate by appointment month (synthetic)": "Show rate por cita, por mes de la cita (sintético)",
    "Funnel, mature cohorts — leads reaching each milestone (synthetic)": "Funnel, cohortes maduras — leads que alcanzan cada hito (sintético)",
    "Realised workload per advisor-month (* = above 150) — synthetic": "Carga real por asesor y mes (* = más de 150) — sintético",
}
FUNNEL_STAGES_ES = {"eligible leads": "leads elegibles", "interview booked": "entrevista agendada",
                    "interview held": "entrevista realizada", "form completed": "formulario completado",
                    "enrollment link sent": "enlace de matrícula enviado", "enrolled": "matriculado"}
COHORT_LABELS_ES = {"mature": "madura", "partial": "parcial", "immature": "inmadura"}


def notebook_charts() -> list[dict]:
    """The chart images of the executed notebook, in notebook order: [{"title", "png"}]."""
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    charts = []
    for cell in nb["cells"]:
        if cell["cell_type"] != "code":
            continue
        m = re.search(r'set_title\("([^"]+)"', "".join(cell["source"]))
        for out in cell.get("outputs", []):
            png = out.get("data", {}).get("image/png")
            if png:
                charts.append({"title": m.group(1) if m else "", "png": base64.b64decode("".join(png) if isinstance(png, list) else png)})
    return charts


def strip_links(markdown: str) -> str:
    """Relative links of the repository documents do not resolve inside the app: keep their text."""
    return re.sub(r"(?<!!)\[([^\]]+)\]\([^)]+\)", r"\1", markdown)


def load() -> dict:
    """Everything the demo shows, computed once from data/ (read only)."""
    res = rc.load_results()
    ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
    decisions = {lang: strip_links((ROOT / "docs" / f"analytical_decisions{'' if lang == 'en' else '.es'}.md")
                                   .read_text(encoding="utf-8")).split("\n", 2)[2]
                 for lang in ("en", "es")}
    return {"results": res, "funnel": metrics.funnel(ctx), "cohorts": metrics.cohort_table(ctx),
            "population": metrics.population_counts(ctx), "charts": notebook_charts(), "decisions": decisions}


def kpi_cards(res: dict, lang: str) -> list[dict]:
    """The eight declarative KPIs as display cards: value, base, population (unit) and time basis."""
    cards = []
    for r in res["eight"]:
        cards.append({"id": r["id"], "label": r["label_en"] if lang == "en" else r["label_es"],
                      "value": rc.fmt_value(r, lang), "base": rc.fmt_base(r, lang),
                      "population": f"{r['population']} ({r['unit']})" if r.get("unit") else r["population"],
                      "time_basis": r["time_basis"], "available": r["status"] == "available",
                      "equals_metrics_py": bool(r.get("equals_metrics_py"))})
    return cards


def metrics_table(res: dict, lang: str):
    """The 47 reference metrics with value, numerator / denominator, unit, population and time basis."""
    import pandas as pd
    rows = []
    for m in res["live47"]:
        r = {**m, "status": "available" if m["value"] is not None else "not_available", "reason": "—"}
        rows.append({"label": m["label_en"] if lang == "en" else m["label_es"],
                     "value": fmt_reference(r, lang), "base": rc.fmt_base(r, lang), "unit": m["unit"],
                     "population": m["population"], "time_basis": m["time_basis"]})
    cols = (["Metric", "Value", "Numerator / denominator", "Unit", "Population", "Time basis"] if lang == "en" else
            ["Métrica", "Valor", "Numerador / denominador", "Unidad", "Población", "Base temporal"])
    return pd.DataFrame(rows).set_axis(cols, axis=1)


def fmt_reference(r: dict, lang: str) -> str:
    """Display value of a reference metric: the project formatter for rates, counts, hours, days and EUR; other kinds
    (mean, median) are shown as recorded, rounded to one decimal."""
    if r["status"] != "available":
        return "—"
    if r["kind"] in ("count", "rate") or r["id"].endswith(("_hours", "_days", "_eur")):
        return rc.fmt_value(r, lang)
    return rc.fmt_number(r["value"], lang, 1)


def funnel_table(funnel, lang: str):
    """metrics.funnel() with localised stage names and percentages."""
    import pandas as pd
    rows = []
    for stage, row in funnel.iterrows():
        prev = row["% of previous"]
        rows.append({"stage": stage if lang == "en" else FUNNEL_STAGES_ES.get(stage, stage),
                     "leads": rc.fmt_number(int(row["leads"]), lang),
                     "of_eligible": rc.fmt_number(100 * row["% of eligible"], lang, 1) + " %",
                     "of_previous": "—" if pd.isna(prev) else rc.fmt_number(100 * prev, lang, 1) + " %"})
    cols = (["Stage", "Leads", "% of eligible", "% of previous stage"] if lang == "en" else
            ["Etapa", "Leads", "% de elegibles", "% de la etapa anterior"])
    return pd.DataFrame(rows).set_axis(cols, axis=1)


def cohort_view(cohorts, lang: str):
    """metrics.cohort_table() with localised maturity labels (which cohorts enter cohort conversions)."""
    import pandas as pd
    df = cohorts.reset_index()[["cohort", "eligible_leads", "mature_leads", "mature_share", "label"]].copy()
    df["cohort"] = df["cohort"].astype(str)
    df["mature_share"] = [rc.fmt_number(100 * v, lang, 1) + " %" for v in df["mature_share"]]
    if lang == "es":
        df["label"] = [COHORT_LABELS_ES.get(v, v) for v in df["label"]]
    cols = (["Cohort", "Eligible leads", "Mature leads", "Mature share", "Maturity"] if lang == "en" else
            ["Cohorte", "Leads elegibles", "Leads maduros", "Proporción madura", "Madurez"])
    return pd.DataFrame(df.values, columns=cols)


def chart_caption(title: str, lang: str) -> str:
    return title if lang == "en" else CHART_TITLES_ES.get(title, title)
