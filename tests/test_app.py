"""Local demo, interface (v1.5.0-app): the Streamlit app runs and shows the expected results in both languages.

Demo local, interfaz: la app se ejecuta y muestra los resultados esperados en los dos idiomas.

Needs Streamlit (requirements-app.txt). In the pinned analytical environment, where Streamlit is not installed, these
tests are skipped; the data layer is tested by tests/test_app_data.py in every environment.
"""
from __future__ import annotations

import pytest

from kpi_helpers import ROOT

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "app" / "streamlit_app.py")


@pytest.fixture(scope="module")
def app_es():
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    return at


def test_runs_without_exceptions_and_shows_the_synthetic_notice(app_es):
    assert not app_es.exception
    assert app_es.title[0].value == "Analítica CRM de admisiones — demo local"
    notices = [w.value for w in app_es.warning]
    assert len(notices) == 2 and all("Datos 100 % sintéticos" in n for n in notices)      # main page and sidebar


def test_four_views(app_es):
    assert [t.label for t in app_es.tabs] == ["Resumen", "Funnel y gráficos", "Métricas de referencia", "Definiciones y límites"]


def test_eight_kpis_with_expected_values(app_es):
    assert [(m.label, m.value) for m in app_es.metric] == [
        ("Leads elegibles", "7.691"), ("Proporción ruta manual", "69,9 %"),
        ("KPI principal: entrevistas realizadas / oportunidades", "45,1 %"), ("Show rate por cita", "69,6 %"),
        ("Formularios / entrevistas realizadas", "42,9 %"), ("Primer intento ≤ 24 h, entradas en fin de semana", "36,3 %"),
        ("Primera respuesta, p90 (horas naturales)", "59,7 h"), ("Ciclo de venta, mediana (días)", "17,0 días")]
    text = " ".join(m.value for m in app_es.markdown)
    assert "8/8" in text and "47/47" in text


def test_tables_and_limits(app_es):
    assert len(app_es.dataframe) == 3                                                 # funnel, 47 metrics, cohorts
    sizes = sorted(len(d.value) for d in app_es.dataframe)
    assert sizes == [6, 12, 47]
    text = " ".join(m.value for m in app_es.markdown)
    assert "Sin filtros interactivos" in text and "No es una plataforma universal" in text


def test_english(app_es):
    app_es.sidebar.radio(key="lang").set_value("English").run()
    assert not app_es.exception
    assert app_es.title[0].value == "Admissions CRM Analytics — local demo"
    assert [m.value for m in app_es.metric][:3] == ["7,691", "69.9 %", "45.1 %"]
    assert [t.label for t in app_es.tabs] == ["Summary", "Funnel and charts", "Reference metrics", "Definitions and limits"]
