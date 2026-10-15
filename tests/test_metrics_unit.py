"""Unit tests for src/metrics.py (F1). Pruebas unitarias del módulo de métricas."""
from __future__ import annotations

import ast
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import checks  # noqa: E402
import metrics  # noqa: E402

CFG = yaml.safe_load((ROOT / "config" / "simulation_params.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def data():
    return checks.load(ROOT / "data")


# ----- utilities ------------------------------------------------------------ #
def test_rate_handles_zero_denominator():
    assert metrics.rate(3, 4) == 0.75
    assert math.isnan(metrics.rate(1, 0))


def test_wilson_interval_edges():
    assert all(math.isnan(x) for x in metrics.wilson_interval(0, 0))
    lo, hi = metrics.wilson_interval(0, 10)
    assert lo == pytest.approx(0, abs=1e-12) and 0 < hi < 0.35
    lo, hi = metrics.wilson_interval(10, 10)
    assert 0.65 < lo < 1 and hi == pytest.approx(1, abs=1e-12)
    lo, hi = metrics.wilson_interval(45, 100)
    assert lo < 0.45 < hi


def test_metric_result_dict_follows_f0_schema():
    r = metrics.MetricResult("x", "X", "X es", "lead", "rate", "pop", "num", "den", "cohort", 1, 0.12345678, np.int64(3), 7)
    d = r.to_dict()
    assert list(d) == ["id", "label_en", "label_es", "unit", "kind", "population", "numerator", "denominator",
                       "time_basis", "definition_ref", "numerator_value", "denominator_value", "value"]
    assert d["value"] == 0.123457 and type(d["numerator_value"]) is int and d["definition_ref"][0].endswith("§1")
    c = metrics.MetricResult("c", "C", "C", "lead", "count", "p", "n", None, "t", 0, np.int64(5), 5).to_dict()
    assert c["value"] == 5 and type(c["value"]) is int and c["denominator_value"] is None
    assert metrics.MetricResult("n", "N", "N", "lead", "mean", "p", "n", "d", "t", 0, float("nan")).to_dict()["value"] is None


def test_reconcile_is_none_safe_and_detects_differences():
    base = {"id": "m", "label_en": "a", "label_es": "a", "unit": "lead", "kind": "median", "population": "p",
            "numerator": "n", "denominator": "d", "time_basis": "t", "definition_ref": ["x"],
            "numerator_value": None, "denominator_value": 10, "value": 1.5}
    ref = {"metrics": [base]}
    assert bool(metrics.reconcile({"metrics": [dict(base)]}, ref).match.all())          # None == None
    assert not bool(metrics.reconcile({"metrics": [dict(base, value=1.500001)]}, ref).match.all())
    assert not bool(metrics.reconcile({"metrics": [dict(base, numerator_value=0)]}, ref).match.all())
    assert metrics.reconcile({"metrics": []}, ref).attrs["missing_from_document"] == ["m"]


# ----- populations and units on a sample of the synthetic data -------------- #
@pytest.fixture(scope="module")
def sample(data):
    leads, acts, gt = data
    keep = set(leads.lead_id.iloc[::7])           # deterministic sample; duplicates/reactivations included
    keep |= set(leads.lead_id[leads.is_duplicate | leads.is_reactivation].iloc[:20])
    L = leads[leads.lead_id.isin(keep)].reset_index(drop=True)
    A = acts[acts.lead_id.isin(keep)].reset_index(drop=True)
    return L, A, gt[gt.lead_id.isin(keep)].reset_index(drop=True)


def test_inputs_are_not_modified(sample):
    L, A, G = sample
    before = (L.copy(), A.copy(), G.copy())
    ctx = metrics.build_context(L, A, G, CFG)
    metrics.funnel(ctx); metrics.governance(ctx); metrics.appointment_metrics(ctx)
    for b, a in zip(before, (L, A, G)):
        pd.testing.assert_frame_equal(b, a)


def test_eligible_excludes_duplicates_and_reactivations(sample):
    L, A, G = sample
    ctx = metrics.build_context(L, A, G, CFG)
    assert not ctx.E.is_duplicate.any() and not ctx.E.is_reactivation.any()
    assert len(ctx.E) == int((~L.is_duplicate & ~L.is_reactivation).sum())
    assert len(ctx.RX) == int(L.is_reactivation.sum())


def test_maturity_boundary_is_exactly_60_x_24_hours(sample):
    L, A, G = sample
    L = L.copy()
    snap = L.snapshot_date.iloc[0]
    e = L.index[~L.is_duplicate & ~L.is_reactivation][:2]
    L.loc[e[0], "created_at"] = snap - pd.Timedelta(days=60)                       # exactly 60 x 24 h -> mature
    L.loc[e[1], "created_at"] = snap - pd.Timedelta(days=60) + pd.Timedelta(seconds=1)
    ctx = metrics.build_context(L, A, G, CFG)
    mature = ctx.E.set_index("lead_id").mature
    assert bool(mature[L.at[e[0], "lead_id"]]) and not bool(mature[L.at[e[1], "lead_id"]])
    assert set(ctx.EM.lead_id) == set(ctx.E.lead_id[ctx.E.mature])


def test_eligible_appointments_exclude_replaced_future_and_ineligible(sample):
    L, A, G = sample
    ctx = metrics.build_context(L, A, G, CFG)
    IE = ctx.IE
    assert IE.replaced_by_activity_id.isna().all()
    assert (IE.interview_scheduled_for <= ctx.SNAP).all()
    assert set(IE.lead_id) <= set(ctx.E.lead_id)
    assert not IE.interview_outcome.isin(["rescheduled", "pending"]).any()
    assert set(ctx.show.interview_outcome) <= {"held", "no_show"}


def test_appointment_and_lead_units_are_not_mixed(sample):
    L, A, G = sample
    ctx = metrics.build_context(L, A, G, CFG)
    ap = metrics.appointment_metrics(ctx)
    assert ap["appointments_held_or_no_show"] == len(ctx.show)                      # appointments
    assert ap["per_lead_denominator"] == ctx.show[ctx.show.mature].lead_id.nunique()  # leads
    rows = {m.id: m for m in metrics.baseline_metrics(ctx)}
    assert rows["show_rate_per_appointment"].unit == "appointment" and rows["show_rate_per_lead"].unit == "lead"


def test_sla_window_and_arrival_split(sample):
    L, A, G = sample
    ctx = metrics.build_context(L, A, G, CFG)
    assert (ctx.Mw.created_at <= ctx.SNAP - pd.Timedelta(hours=24)).all()
    split = metrics.sla_by_arrival(ctx)
    assert int(split.leads.sum()) == len(ctx.Mw)


def test_bot_route_half_comparison_on_a_tiny_frame():
    rows = []
    for month, n, held in ((3, 4, 2), (8, 4, 4)):
        for i in range(n):
            rows.append({"is_duplicate": False, "is_reactivation": False, "entry_path": "bot_booked",
                         "created_at": f"2025-{month:02d}-10", "entered_interview_held_at": "2025-01-01" if i < held else None})
    rows.append({"is_duplicate": True, "is_reactivation": False, "entry_path": "bot_booked",
                 "created_at": "2025-03-10", "entered_interview_held_at": None})                 # excluded
    out = metrics.bot_route_half_comparison(pd.DataFrame(rows))
    assert out["Jan–Jun"] == 0.5 and out["Jul–Oct"] == 1.0 and out["z"] > 0


def test_results_are_deterministic(sample):
    L, A, G = sample
    a = [m.to_dict() for m in metrics.baseline_metrics(metrics.build_context(L, A, G, CFG))]
    b = [m.to_dict() for m in metrics.baseline_metrics(metrics.build_context(L, A, G, CFG))]
    assert a == b


def test_module_has_no_side_effects_or_network():
    tree = ast.parse((ROOT / "src" / "metrics.py").read_text(encoding="utf-8"))
    names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "print" not in names
    assert not attrs & {"write_text", "write_bytes", "to_csv", "to_json", "savefig", "show", "seed", "random"}
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                for a in (n.names if isinstance(n, ast.Import) else [ast.alias(n.module or "")])}
    assert imported <= {"__future__", "hashlib", "dataclasses", "functools", "pathlib", "numpy", "pandas", "yaml",
                        "checks", "src"}, imported


def test_new_f1_code_has_no_network_or_crm_imports():
    forbidden = {"requests", "urllib", "http", "socket", "httpx", "aiohttp", "hubspot", "simple_salesforce"}
    for rel in ("src/metrics.py", "scripts/export_metrics.py", "scripts/f1_run.py", "scripts/build_notebook.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module.split(".")[0])
        assert not mods & forbidden, (rel, mods & forbidden)
