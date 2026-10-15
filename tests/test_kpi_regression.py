"""The eight F3.0 KPIs of the engine vs F0, F1, F2 and src/metrics.py on the generated data.

Los ocho KPIs del motor frente a F0, F1, F2 y src/metrics.py con los datos generados.

Equality is exact on the F0 document shape: ids, descriptive fields, numerators, denominators and values at the
reference rounding of 6 decimals (no extra tolerance). src/metrics.py is computed in memory; no reference is written.
"""
from __future__ import annotations

import json

import pytest

from kpi_helpers import KPI_IDS, ROOT, SPEC_PATH
import metrics
from canonical import mapping
from canonical.adapters import admissions as ad
from canonical.validate import validate
from kpispec import engine
from kpispec.spec import load_spec


@pytest.fixture(scope="module")
def engine_docs():
    spec = load_spec(SPEC_PATH)
    can = validate(mapping.map_directory(ROOT / "data"))
    ad.check_profile(can)
    res = engine.evaluate(spec, can)
    assert all(r["status"] == "available" for r in res)
    return {r["id"]: engine.baseline_shape(spec, r) for r in res}


def _reference(rel):
    doc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    rows = doc["metrics"] if "metrics" in doc else [{k: v for k, v in m.items() if k != "status"} for m in doc["baseline_metrics"]]
    return {m["id"]: m for m in rows}


@pytest.mark.parametrize("ref", ["baseline/metrics_v1.json", "reports/f1/metrics_f1.json", "reports/f2/metrics_f2_canonical.json"])
def test_engine_equals_frozen_references(engine_docs, ref):
    refs = _reference(ref)
    for kid in KPI_IDS:
        assert engine_docs[kid] == refs[kid], (ref, kid, engine_docs[kid], refs[kid])


def test_engine_equals_metrics_py_in_memory(engine_docs):
    ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
    live = {m.id: m.to_dict() for m in metrics.baseline_metrics(ctx)}
    for kid in KPI_IDS:
        assert engine_docs[kid] == live[kid], kid


def test_expected_headline_values(engine_docs):
    got = {k: (v["value"], v["numerator_value"], v["denominator_value"]) for k, v in engine_docs.items()}
    assert got == {
        "eligible_leads": (7691, 7691, None),
        "share_manual_route": (0.698739, 5374, 7691),
        "main_kpi_interviews_held_over_opportunities": (0.450593, 2923, 6487),
        "show_rate_per_appointment": (0.695661, 3431, 4932),
        "forms_over_interviews_held": (0.429353, 1255, 2923),
        "sla_first_attempt_24h_manual_weekend": (0.362911, 364, 1003),
        "first_response_p90_hours": (59.662778, None, 5243),
        "sales_cycle_median_days": (17.043947, None, 684),
    }
