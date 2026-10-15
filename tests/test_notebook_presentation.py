"""The notebook presents results of src/metrics.py and does not recompute them (F1).

El notebook presenta los resultados de src/metrics.py y no los recalcula.

Primary checks (acceptance):
  1. Execution trace: the notebook's code cells are executed in-process, in order, with every public function of
     `metrics` wrapped to record its calls and return values, and `display` captured. Every expected function must
     be called, and every displayed table (Styler data, DataFrame or Series) must come from a recorded return value:
     each column equals a column / series returned by `metrics`, or (for the seed-robustness table, assembled from
     several calls) each value equals a scalar returned by `metrics`. The only all-text table is the key-figures one,
     whose strings must equal the formatting of `metrics.key_figures`.
  2. Executed notebook (fresh kernel, written by scripts/build_notebook.py): no errors, sequential execution counts,
     key figures and the F0 reconciliation line equal the module's results, and every figure quoted in the
     conclusions and both READMEs appears in the outputs.
Orientative check: a static scan of the cells for pandas aggregation calls. Any remaining one must be in ALLOWED with
a reason and have a focused test.
"""
from __future__ import annotations

import ast
import functools
import importlib.util
import inspect
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402

NB = ROOT / "notebooks" / "admissions_analysis.ipynb"
EXPECTED_CALLS = {
    "load_context", "population_counts", "validation_summary", "cohort_table", "sla_summary", "sla_by_arrival",
    "bot_pre_interview", "main_kpi_by_cohort", "main_kpi_totals", "appointment_metrics", "personal_whatsapp_association",
    "show_rate_by_month", "bot_route_half_comparison", "funnel", "directional_rates", "sales_cycle", "segment_table",
    "workload", "advisor_table", "advisor_activity_counts", "lost_reasons", "nurture_summary", "governance", "finance",
    "baseline_document", "reconciliation_summary", "reconcile", "key_figures"}
AGGREGATIONS = {"groupby", "merge", "pivot_table", "crosstab", "agg", "aggregate", "apply", "value_counts", "mean",
                "median", "quantile", "sum", "count", "nunique", "size", "max", "min", "std", "cut", "resample", "rolling"}
# Remaining pandas aggregation calls in notebook cells, each with the reason it does not duplicate an official metric.
ALLOWED = {("max", "fun.leads"): "x-axis limit of the funnel chart (presentation only; the counts come from metrics.funnel)"}


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_notebook", ROOT / "scripts" / "build_notebook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def code_cells():
    nb = _load_builder().build()
    return [c.source for c in nb.cells if c.cell_type == "code"]


# --------------------------------------------------------------------------- #
# 1. Execution trace (primary)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def trace(code_cells):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    calls, returns = [], []
    originals = {}
    for name, fn in inspect.getmembers(metrics, inspect.isfunction):
        if fn.__module__ != metrics.__name__ or name.startswith("_"):
            continue
        originals[name] = fn

        def wrap(f, n):
            @functools.wraps(f)
            def inner(*a, **k):
                out = f(*a, **k)
                calls.append(n); returns.append(out)
                return out
            return inner
        setattr(metrics, name, wrap(fn, name))
    shown = []
    ns = {"display": shown.append, "__name__": "__main__"}
    show_orig = plt.show
    plt.show = lambda *a, **k: plt.close("all")
    cwd = Path.cwd()
    try:
        import os
        os.chdir(ROOT / "notebooks")
        for src in code_cells:
            exec(compile(src, "<notebook cell>", "exec"), ns)
    finally:
        os.chdir(cwd)
        plt.show = show_orig
        for n, f in originals.items():
            setattr(metrics, n, f)
    return {"calls": calls, "returns": returns, "shown": shown, "ns": ns}


def _columns(obj):
    """Yield every 1-D value sequence carried by a return value (DataFrame columns, Series, nested dict values)."""
    if isinstance(obj, pd.DataFrame):
        for c in obj.columns:
            yield list(obj[c])
    elif isinstance(obj, pd.Series):
        yield list(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _columns(v)


def _scalars(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _scalars(v)
    elif isinstance(obj, (int, float, np.integer, np.floating)) and not isinstance(obj, bool):
        yield float(obj)


def _same(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        xn = x is None or (isinstance(x, float) and np.isnan(x))
        yn = y is None or (isinstance(y, float) and np.isnan(y))
        if xn or yn:
            if not (xn and yn):
                return False
        elif isinstance(x, (int, float, np.number)) and isinstance(y, (int, float, np.number)) and not isinstance(x, bool):
            if not np.isclose(float(x), float(y), rtol=1e-12, atol=0):
                return False
        elif x != y:
            return False
    return True


def test_every_expected_metrics_function_is_called(trace):
    missing = EXPECTED_CALLS - set(trace["calls"])
    assert not missing, f"notebook does not call: {sorted(missing)}"


def test_every_displayed_table_comes_from_metrics(trace):
    recorded = [col for r in trace["returns"] for col in _columns(r)]
    scalars = [s for r in trace["returns"] for s in _scalars(r)]
    text_only = []
    for obj in trace["shown"]:
        data = obj.data if hasattr(obj, "data") and hasattr(obj, "format") else obj   # Styler -> its data
        frame = data.to_frame() if isinstance(data, pd.Series) else data
        assert isinstance(frame, pd.DataFrame), type(obj)
        numeric_cols = [c for c in frame.columns if pd.api.types.is_numeric_dtype(frame[c])
                        or frame[c].map(lambda v: v is None or isinstance(v, (int, float, np.number, bool))).all()]
        if not numeric_cols:
            text_only.append(frame); continue
        for c in frame.columns:
            col = list(frame[c])
            ok = any(_same(col, r) for r in recorded)
            if not ok and c in numeric_cols:   # tables assembled from several calls (seed robustness)
                ok = all(any(np.isclose(float(v), s, rtol=1e-12, atol=0) for s in scalars) for v in col)
            assert ok, f"displayed column {c!r} does not come from a metrics return value"
    assert len(text_only) == 1, "only the key-figures table may be text-only"


def test_key_figures_table_formats_module_values(trace):
    k = metrics.key_figures(metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml"))
    pct = lambda x: f"{x:.1%}"
    expected = [f"{k['eligible_leads']:,}", f"{k['mature_eligible_leads']:,}", pct(k["main_kpi"]),
                f"{pct(k['main_kpi_manual'])} / {pct(k['main_kpi_bot'])}", pct(k["show_rate_per_appointment"]),
                pct(k["forms_over_held"]), pct(k["enrollments_over_held"]), pct(k["sla_24h_manual"]),
                k["advisor_months_over_150_realised"], f"{k['average_net_price']:,.0f}"]
    table = [o for o in trace["shown"] if isinstance(o, pd.DataFrame) and list(o.columns) == ["synthetic value"]]
    assert len(table) == 1 and list(table[0]["synthetic value"]) == expected


def test_notebook_writes_no_files(code_cells):
    for src in code_cells:
        tree = ast.parse(src)
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        assert not attrs & {"write_text", "write_bytes", "to_csv", "to_json", "savefig", "dump"}, attrs
        assert "baseline/metrics_v1.json\").write" not in src


def test_notebook_does_not_import_checks_or_recompute_helpers(code_cells):
    joined = "\n".join(code_cells)
    assert "import checks" not in joined and "checks." not in joined
    for helper in ("def rate", "def wilson", "def seg(", "def adv_table", "def bot_halves"):
        assert helper not in joined, helper


# --------------------------------------------------------------------------- #
# 2. Executed notebook (fresh kernel)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def executed():
    import nbformat
    if not NB.exists():
        pytest.fail("executed notebook missing: run `python scripts/build_notebook.py` first")
    return nbformat.read(NB, as_version=4)


def _outputs_text(nb):
    out = ""
    for c in nb.cells:
        if c.cell_type != "code":
            continue
        for o in c.outputs:
            if o.output_type == "stream":
                out += o.text
            elif "data" in o:
                out += o["data"].get("text/html", "") + o["data"].get("text/plain", "")
    return out


def test_executed_top_to_bottom_without_errors(executed):
    code = [c for c in executed.cells if c.cell_type == "code"]
    assert [c.execution_count for c in code] == list(range(1, len(code) + 1))
    assert not any(o.output_type == "error" for c in code for o in c.outputs)


def test_executed_notebook_shows_47_of_47_reconciliation(executed):
    assert "Metrics: 47 · matching F0: 47 · missing from F1: none" in _outputs_text(executed)
    assert "input hashes identical to F0: True" in _outputs_text(executed)


def test_quoted_figures_appear_in_executed_outputs(executed):
    flat = _outputs_text(executed).replace(" ", "")
    conc = (ROOT / "scripts" / "notebook_conclusions.md").read_text(encoding="utf-8")
    en, es = conc.split("### ES")
    def nums(text, dec):
        if dec == ".":
            n = re.findall(r"\d[\d,]*\.\d+ ?%|\d[\d,]*\.\d+ ?h\b|€\d,\d{3}|\b\d{1,3},\d{3}\b", text)
            return [x.replace(" ", "").replace("€", "") for x in n]
        n = re.findall(r"\d[\d.]*,\d+ ?%|\d[\d.]*,\d+ ?h\b|\d\.\d{3} €|\b\d{1,3}\.\d{3}\b", text)
        return [x.replace(" ", "").replace("€", "").replace(".", "#").replace(",", ".").replace("#", ",") for x in n]
    for name, text, dec in (("conclusions EN", en, "."), ("conclusions ES", es, ","),
                            ("README.md", (ROOT / "README.md").read_text(encoding="utf-8"), "."),
                            ("README.es.md", (ROOT / "README.es.md").read_text(encoding="utf-8"), ",")):
        missing = [x for x in nums(text, dec) if x not in flat and x.replace("h", "") not in flat]
        assert not missing, (name, missing)


# --------------------------------------------------------------------------- #
# 3. Orientative static scan + focused test for the allowed exception
# --------------------------------------------------------------------------- #
def _aggregation_calls(code_cells):
    found = []
    for src in code_cells:
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in AGGREGATIONS:
                found.append((n.func.attr, ast.unparse(n.func.value)))
    return found


def test_static_scan_only_documented_aggregations(code_cells):
    found = _aggregation_calls(code_cells)
    undocumented = [f for f in found if f not in ALLOWED]
    assert not undocumented, f"aggregation in notebook cells without a documented reason: {undocumented}"


def test_allowed_max_is_only_an_axis_limit(code_cells):
    src = next(s for s in code_cells if "metrics.funnel(ctx)" in s)
    lines = [l for l in src.splitlines() if "fun.leads.max()" in l]
    assert lines and all("ax.set_xlim(" in l for l in lines)
