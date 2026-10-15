"""KPI availability (F2): requirements, reason codes and the not_available shape (no value, never zero).

Disponibilidad de KPIs: requisitos, códigos de motivo y forma de not_available (sin valor, nunca cero).
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402
from canonical import availability  # noqa: E402

REQ = availability.load_requirements()
CAPS = ["stage_milestones", "stage_transitions", "is_automated", "appointments"]


def caps(**kw):
    base = {"history_mode": "x", "stage_milestones": True, "stage_transitions": True, "is_automated": True, "appointments": True}
    return {**base, **kw}


def test_requirements_cover_the_47_baseline_metrics_and_the_7_history_indicators():
    ids = [m["id"] for m in json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8"))["metrics"]]
    assert len(ids) == 47
    assert set(REQ["requirements"]) == set(ids) | set(REQ["catalogue"]["history"])
    assert set(REQ["catalogue"]["metrics"]) <= set(ids)
    for r in REQ["requirements"].values():
        assert set(r) <= set(CAPS)


def test_catalogue_is_24_plus_7():
    assert len(REQ["catalogue"]["metrics"]) == 24 and len(REQ["catalogue"]["history"]) == 7
    assert REQ["catalogue"]["capabilities_without_expected_value"] == ["time_in_stage"]


def test_reason_codes():
    assert REQ["reason_codes"] == {"stage_milestones": "HM", "stage_transitions": "HF", "is_automated": "AUT", "appointments": "APT"}


@pytest.mark.parametrize("combo", list(itertools.product([True, False], repeat=4)))
def test_every_capability_combination_covers_each_id_once(combo):
    c = caps(**dict(zip(CAPS, combo)))
    m = availability.matrix(c)
    ids = [e["id"] for e in m]
    assert ids == availability.catalogue() and len(set(ids)) == 31
    for e in m:
        if e["status"] == "available":
            assert set(e) == {"id", "status"}
        else:
            assert set(e) == {"id", "status", "reason", "missing"} and e["missing"]
            assert all(not c[x] for x in e["missing"])


def test_multiple_missing_requirements_join_reasons():
    st = availability.status("followup_48h_manual_advisor", caps(stage_milestones=False, is_automated=False))
    assert st["reason"] == "HM+AUT" and st["missing"] == ["stage_milestones", "is_automated"]


def test_leak_detector():
    ok = [{"id": "x", "status": "not_available", "reason": "HM", "missing": ["stage_milestones"]}]
    availability.check_no_leak(ok)
    for bad_key in ("value", "numerator", "denominator", "numerator_value", "denominator_value"):
        with pytest.raises(AssertionError):
            availability.check_no_leak([{**ok[0], bad_key: 0}])


def test_unknown_kpi_is_an_error():
    with pytest.raises(KeyError):
        availability.status("not_a_kpi", caps())


def test_admissions_metrics_module_unchanged_ids():
    """The requirement file names exactly the ids produced by src/metrics.py (no rename, no new metric)."""
    import inspect
    src = inspect.getsource(metrics.baseline_metrics)
    for mid in REQ["catalogue"]["metrics"]:
        assert f'add("{mid}"' in src, mid
