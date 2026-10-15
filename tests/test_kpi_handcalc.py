"""The eight F3.0 KPIs on the official 12-record fixture, five variants (engine only, no src/metrics.py).

Los ocho KPIs de F3.0 sobre el fixture oficial de 12 registros, cinco variantes (solo el motor).

Expected statuses and reasons come from expected.json (the approved 31-indicator matrix) and the values from its
hand-calculated sections; eligible_leads is populations.eligible.
"""
from __future__ import annotations

import json

import pytest

from kpi_helpers import FIX, KPI_IDS, VARIANTS, evaluate, fixture

EXP = json.loads((FIX / "expected.json").read_text(encoding="utf-8"))
REF = {**EXP["metrics_all_eligible"], **EXP["metrics_mature_eligible"],
       "eligible_leads": {"value": EXP["populations"]["eligible"], "numerator": EXP["populations"]["eligible"], "denominator": None}}
COUNTS = {"v_full": (8, 0), "v_milestone": (8, 0), "v_snapshot": (6, 2), "v_no_automated": (6, 2), "v_no_appointments": (7, 1)}


def r6(v):
    return round(v, 6) if isinstance(v, float) else v


@pytest.mark.parametrize("variant", VARIANTS)
def test_variant_matrix_and_values(variant):
    res = evaluate(fixture(variant))
    v = EXP["variants"][variant]
    na = {e["id"]: e["reason"] for e in v["not_available"]}
    for kid in KPI_IDS:
        r = res[kid]
        if kid in na:
            assert r["status"] == "not_available" and r["reason"] == na[kid], (variant, kid, r)
        else:
            assert kid == "eligible_leads" or kid in v["available"], (variant, kid)
            assert r["status"] == "available", (variant, kid, r)
            got = {f: r6(r[f]) for f in ("value", "numerator", "denominator")}
            assert got == {f: r6(REF[kid][f]) for f in ("value", "numerator", "denominator")}, (variant, kid)
    avail = sum(r["status"] == "available" for r in res.values())
    assert (avail, len(res) - avail) == COUNTS[variant]


def test_handcalc_runs_without_metrics():
    """This module and its helpers never load src/metrics.py: run them in a fresh interpreter and check sys.modules."""
    import subprocess
    import sys
    from kpi_helpers import ROOT
    code = ("import sys; sys.path.insert(0, 'tests')\n"
            "import test_kpi_handcalc as t\n"
            "for v in t.VARIANTS: t.test_variant_matrix_and_values(v)\n"
            "print(sorted(m for m in ('metrics', 'src.metrics') if m in sys.modules))\n")
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip().splitlines()[-1] == "[]", p.stdout
