"""Local demo of Admissions CRM Analytics (v1.5.0-app). Synthetic data only; no network, no uploads, no CRM.

Demo local de Admissions CRM Analytics. Solo datos sintéticos; sin red, sin subida de archivos, sin CRM.

Run from the project folder:  streamlit run app/streamlit_app.py
Every figure comes from app/app_data.py, which reads what the project already computes (no formula is added here).
The data are loaded once per session from data/; the generator, the tests and the release run are never executed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app_data  # noqa: E402

T = {
    "es": {
        "title": "Analítica CRM de admisiones — demo local",
        "subtitle": "Funnel de admisiones B2C de certificados online: lead → contacto → entrevista → formulario → matrícula.",
        "synthetic": "**Datos 100 % sintéticos** (semilla 42). No describen ninguna empresa, persona ni mercado reales; "
                     "los resultados reflejan los parámetros del escenario y no se hacen afirmaciones causales.",
        "tabs": ["Resumen", "Funnel y gráficos", "Métricas de referencia", "Definiciones y límites"],
        "kpis": "Ocho KPIs del motor declarativo",
        "kpis_note": "Cada KPI declarativo es idéntico al valor del motor de referencia (`src/metrics.py`).",
        "population": "Población", "time_basis": "Base temporal", "base": "Numerador / denominador",
        "checks": "Comprobaciones en esta sesión",
        "check8": "KPIs declarativos iguales a src/metrics.py", "check47": "métricas de referencia iguales a la línea base congelada F0",
        "counts": "Leads elegibles: {e} · leads elegibles maduros (≥ 60 días en la fecha de corte {snap}): {m}",
        "funnel": "Funnel de las cohortes maduras", "funnel_note": "Leads elegibles maduros que alcanzan cada hito (`metrics.funnel`).",
        "charts": "Gráficos del análisis", "charts_note": "Las mismas imágenes del notebook ejecutado y versionado; no se vuelven a dibujar.",
        "reference": "Las 47 métricas del motor de referencia",
        "reference_note": "Calculadas por `src/metrics.py`; definiciones de población y base temporal en inglés, como en la referencia.",
        "scope": "Alcance y límites",
        "scope_items": [
            "47 métricas las calcula el motor de referencia; solo 8 están configuradas en el motor declarativo. No es una plataforma universal: solo está probado el perfil de admisiones.",
            "Sin conexión a ningún CRM, sin credenciales y sin datos reales. UTC todavía no está soportado por el adaptador.",
            "**Sin filtros interactivos:** las funciones actuales calculan cada métrica sobre su población completa; filtrar por fuente, ruta o periodo exigiría recalcular poblaciones y denominadores con una ruta nueva que el motor no tiene. Para no mezclar poblaciones, la demo no los ofrece.",
            "Gráficos: verificación gráfica estricta en Linux; en otros sistemas las imágenes renderizadas pueden diferir en píxeles (aquí se muestran las versionadas).",
        ],
        "cohorts": "Madurez de las cohortes", "cohorts_note": "Solo las cohortes maduras entran en las conversiones por cohorte (`metrics.cohort_table`).",
        "decisions": "Decisiones analíticas",
        "footer": "Código: MIT · contenido: CC BY 4.0 · fuentes Inter: SIL OFL 1.1 — Carlos Eduardo Rodriguez Chimienti — Admissions CRM Analytics · ",
        "lang": "Idioma",
    },
    "en": {
        "title": "Admissions CRM Analytics — local demo",
        "subtitle": "B2C admissions funnel for online certificates: lead → contact → interview → form → enrollment.",
        "synthetic": "**100 % synthetic data** (seed 42). They describe no real company, person or market; the results "
                     "reflect the scenario parameters and no causal claim is made.",
        "tabs": ["Summary", "Funnel and charts", "Reference metrics", "Definitions and limits"],
        "kpis": "Eight KPIs of the declarative engine",
        "kpis_note": "Each declarative KPI is identical to the value of the reference engine (`src/metrics.py`).",
        "population": "Population", "time_basis": "Time basis", "base": "Numerator / denominator",
        "checks": "Checks in this session",
        "check8": "declarative KPIs equal to src/metrics.py", "check47": "reference metrics equal to the frozen F0 baseline",
        "counts": "Eligible leads: {e} · mature eligible leads (≥ 60 days at the snapshot {snap}): {m}",
        "funnel": "Funnel of the mature cohorts", "funnel_note": "Mature eligible leads reaching each milestone (`metrics.funnel`).",
        "charts": "Charts of the analysis", "charts_note": "The same images as the versioned executed notebook; not redrawn.",
        "reference": "The 47 metrics of the reference engine",
        "reference_note": "Computed by `src/metrics.py`; population and time-basis definitions as in the reference.",
        "scope": "Scope and limits",
        "scope_items": [
            "47 metrics are computed by the reference engine; only 8 are configured in the declarative engine. This is not a universal platform: only the admissions profile is tested.",
            "No CRM connection, no credentials and no real data. UTC is not supported by the adapter yet.",
            "**No interactive filters:** the current functions compute each metric on its whole population; filtering by source, route or period would need populations and denominators recomputed through a new route the engine does not have. To avoid mixing populations, the demo does not offer them.",
            "Charts: strict graphical verification on Linux; on other systems rendered images can differ in pixels (the versioned ones are shown here).",
        ],
        "cohorts": "Cohort maturity", "cohorts_note": "Only mature cohorts enter cohort conversions (`metrics.cohort_table`).",
        "decisions": "Analytical decisions",
        "footer": "Code: MIT · content: CC BY 4.0 · Inter fonts: SIL OFL 1.1 — Carlos Eduardo Rodriguez Chimienti — Admissions CRM Analytics · ",
        "lang": "Language",
    },
}

st.set_page_config(page_title="Admissions CRM Analytics — demo", layout="wide")


@st.cache_resource(show_spinner=False)
def load_data() -> dict:
    return app_data.load()


lang = "es" if st.sidebar.radio(T["es"]["lang"] + " / " + T["en"]["lang"], ["Español", "English"], key="lang") == "Español" else "en"
L = T[lang]
with st.spinner("…"):
    D = load_data()
res = D["results"]

st.sidebar.warning(L["synthetic"])
st.title(L["title"])
st.caption(L["subtitle"])
st.warning(L["synthetic"])

summary, funnel_tab, reference_tab, limits_tab = st.tabs(L["tabs"])

with summary:
    st.subheader(L["kpis"])
    st.caption(L["kpis_note"])
    cards = app_data.kpi_cards(res, lang)
    for row in range(0, len(cards), 4):
        for col, card in zip(st.columns(4), cards[row:row + 4]):
            with col:
                st.metric(card["label"], card["value"], help=card["label"])
                st.caption(f"{L['base']}: {card['base']}  \n{L['population']}: {card['population']}  \n"
                           f"{L['time_basis']}: {card['time_basis']}")
    st.divider()
    pop = D["population"]
    st.markdown(L["counts"].format(e=app_data.rc.fmt_number(pop["eligible_leads"], lang),
                                   m=app_data.rc.fmt_number(pop["mature_eligible_leads"], lang), snap=str(pop["snapshot"])))
    ok8 = sum(c["equals_metrics_py"] for c in cards)
    st.markdown(f"**{L['checks']}:** {ok8}/8 {L['check8']} · {res['metrics_equal_f0']}/{res['metrics_total']} {L['check47']}")

with funnel_tab:
    st.subheader(L["funnel"])
    st.caption(L["funnel_note"])
    st.dataframe(app_data.funnel_table(D["funnel"], lang), hide_index=True, width="stretch")
    st.subheader(L["charts"])
    st.caption(L["charts_note"])
    for chart in D["charts"]:
        st.image(chart["png"], caption=app_data.chart_caption(chart["title"], lang))

with reference_tab:
    st.subheader(L["reference"])
    st.caption(L["reference_note"])
    st.dataframe(app_data.metrics_table(res, lang), hide_index=True, width="stretch", height=600)

with limits_tab:
    st.subheader(L["scope"])
    for item in L["scope_items"]:
        st.markdown(f"- {item}")
    st.subheader(L["cohorts"])
    st.caption(L["cohorts_note"])
    st.dataframe(app_data.cohort_view(D["cohorts"], lang), hide_index=True, width="stretch")
    st.subheader(L["decisions"])
    st.markdown(D["decisions"][lang])

st.divider()
st.caption(L["footer"] + app_data.REPO_URL)
