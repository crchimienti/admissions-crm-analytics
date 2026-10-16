"""Local demo, data layer (v1.5.0-app): app/app_data.py shows what the project already computes, adds no formula,
writes nothing and opens no connection. Runs in the pinned analytical environment (no Streamlit needed).

Demo local, capa de datos: muestra lo que el proyecto ya calcula, sin fórmulas nuevas, sin escribir y sin red.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import subprocess
import sys

import pytest

from kpi_helpers import ROOT

sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "scripts"))
import app_data  # noqa: E402
import release_checks as rc  # noqa: E402

APP_FILES = ["app/app_data.py", "app/streamlit_app.py"]


@pytest.fixture(scope="module")
def loaded():
    return app_data.load()


def test_eight_kpis_are_the_project_results(loaded):
    cards = app_data.kpi_cards(loaded["results"], "en")
    assert [c["id"] for c in cards] == [r["id"] for r in loaded["results"]["eight"]]
    assert all(c["available"] and c["equals_metrics_py"] for c in cards)
    assert [c["value"] for c in cards] == ["7,691", "69.9 %", "45.1 %", "69.6 %", "42.9 %", "36.3 %", "59.7 h", "17.0 days"]
    es = [c["value"] for c in app_data.kpi_cards(loaded["results"], "es")]
    assert es == ["7.691", "69,9 %", "45,1 %", "69,6 %", "42,9 %", "36,3 %", "59,7 h", "17,0 días"]
    assert loaded["results"]["metrics_equal_f0"] == loaded["results"]["metrics_total"] == 47


def test_cards_and_readme_show_the_same_values(loaded):
    """The values the demo shows are the ones in the verified README results block."""
    for lang, name in (("en", "README.md"), ("es", "README.es.md")):
        block = (ROOT / name).read_text(encoding="utf-8").split(rc.RESULTS_START)[1].split(rc.RESULTS_END)[0]
        for c in app_data.kpi_cards(loaded["results"], lang):
            assert f"| {c['label']} | {c['value']} |" in block, (name, c["id"])


def test_reference_table_has_the_47_metrics(loaded):
    for lang in ("en", "es"):
        df = app_data.metrics_table(loaded["results"], lang)
        assert len(df) == 47 and df.iloc[:, 1].ne("—").all()
    live = {m["id"]: m for m in loaded["results"]["live47"]}
    row = app_data.metrics_table(loaded["results"], "en").iloc[[m["id"] for m in loaded["results"]["live47"]].index("followup_48h_manual_advisor")]
    assert row["Value"] == "62.2 %" and row["Numerator / denominator"] == "2,118 / 3,403"
    assert live["followup_48h_manual_advisor"]["denominator_value"] == 3403


def test_funnel_and_cohorts_come_from_metrics(loaded):
    f = app_data.funnel_table(loaded["funnel"], "en")
    assert list(f["Leads"]) == ["6,487", "3,651", "2,923", "1,255", "1,042", "684"]
    assert f.iloc[2]["% of eligible"] == "45.1 %"                                   # = main KPI
    c = app_data.cohort_view(loaded["cohorts"], "es")
    assert list(c["Madurez"])[-3:] == ["madura", "parcial", "inmadura"] and len(c) == 12


def test_charts_are_the_versioned_notebook_images(loaded):
    nb = json.loads((ROOT / "notebooks" / "admissions_analysis.ipynb").read_text(encoding="utf-8"))
    pngs = [base64.b64decode("".join(o["data"]["image/png"])) for c in nb["cells"] for o in c.get("outputs", [])
            if "image/png" in o.get("data", {})]
    assert [ch["png"] for ch in loaded["charts"]] == pngs and len(pngs) == 5
    docs_img = {p.read_bytes() for p in (ROOT / "docs" / "img").glob("*.png")}
    assert docs_img <= set(pngs)                                                      # README figures are among them
    assert all(app_data.chart_caption(ch["title"], "es") != ch["title"] for ch in loaded["charts"])


def test_definitions_are_the_project_documents(loaded):
    for lang in ("en", "es"):
        text = loaded["decisions"][lang]
        assert text.startswith("# ") and "](" not in text                             # relative links reduced to text
    assert "Analytical decisions" in loaded["decisions"]["en"] and "Decisiones analíticas" in loaded["decisions"]["es"]


def _imports(rel):
    mods = set()
    for n in ast.walk(ast.parse((ROOT / rel).read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    return mods


@pytest.mark.parametrize("rel", APP_FILES)
def test_app_code_has_no_network_generator_tests_or_writes(rel):
    mods = _imports(rel)
    assert not mods & {"requests", "urllib", "http", "socket", "httpx", "aiohttp", "subprocess", "generate_data",
                       "pytest", "release_run", "hubspot", "simple_salesforce"}, mods
    src = (ROOT / rel).read_text(encoding="utf-8")
    for call in ("write_text(", "write_bytes(", "to_csv(", "savefig(", "file_uploader(", "open("):
        assert call not in src, (rel, call)
    if rel == "app/app_data.py":
        assert "streamlit" not in mods                                               # testable without the app environment


def test_loading_writes_nothing():
    def snapshot():
        return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
    before = snapshot()
    code = "import sys; sys.dont_write_bytecode = True; sys.path.insert(0, 'app'); import app_data; app_data.load()"
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    assert snapshot() == before


def test_streamlit_config_is_local_and_without_usage_statistics():
    cfg = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'address = "localhost"' in cfg and "gatherUsageStats = false" in cfg


def test_cloud_dependency_file_only_points_to_the_app_requirements():
    """app/requirements.txt (v1.5.1-app) is the file Streamlit Community Cloud reads next to the entrypoint: it adds or
    changes nothing, it only points to requirements-app.txt; the root requirements files stay as they are."""
    lines = [l for l in (ROOT / "app" / "requirements.txt").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    assert lines == ["-r ../requirements-app.txt"]


def test_app_requirements_extend_the_lock_without_changing_it():
    lines = [l for l in (ROOT / "requirements-app.txt").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    assert lines[0] == "-r requirements-lock.txt"
    pins = {l.split("==")[0].lower(): l.split("==")[1].split()[0] for l in lines[1:]}
    assert pins["streamlit"] == "1.65.0" and all("==" in l for l in lines[1:])
    lock = {l.split("==")[0].lower() for l in (ROOT / "requirements-lock.txt").read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("#")}
    assert not set(pins) & lock                                                       # no pinned version is overridden
    assert "streamlit" not in lock
