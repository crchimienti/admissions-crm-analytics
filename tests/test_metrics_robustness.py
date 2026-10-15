"""Robustness of src/metrics.py on degenerate inputs (authorised fix, v1.2.1-f2).

Robustez de src/metrics.py con entradas degeneradas (corrección autorizada, v1.2.1-f2).

Three situations are kept apart and never turned into a valid zero:
  * module absent      (HM, HF, AUT, APT)  a table or column the KPI needs is missing -> decided before computing
  * zero denominator   (DEN0)              inputs exist but the rate's denominator is 0
  * insufficient data  (INSUF)             a median / mean / percentile has no observation
A true zero (numerator 0 over a positive denominator) stays an available value of 0.
The 47 values on the generated data are checked unchanged by tests/test_regression_f0.py and test_regression_f1.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import read_canonical  # noqa: E402
from canonical.validate import validate  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "canonical_handcalc"
VARIANTS = ["v_full", "v_milestone", "v_snapshot", "v_no_automated", "v_no_appointments"]


def load_modified(variant, change):
    can = read_canonical(FIX / variant)
    change(can.tables)
    can = validate(can)
    ad.check_profile(can)
    return can


def by_id(out):
    return {e["id"]: e for e in out["baseline_metrics"]}


def test_rate_never_divides_by_zero():
    assert np.isnan(metrics.rate(0, 0)) and np.isnan(metrics.rate(np.int64(3), 0))
    assert metrics.rate(np.int64(3), np.int64(4)) == 0.75


@pytest.mark.parametrize("variant", VARIANTS)
def test_baseline_metrics_run_on_every_variant_without_inf(variant):
    res = metrics.baseline_metrics(ad.build_context(ad.load(FIX / variant)))
    assert len(res) == 47
    for r in res:
        assert not (isinstance(r.value, (float, np.floating)) and np.isinf(r.value)), r.id


def test_zero_denominator_without_history_is_undefined_not_an_error():
    """v_snapshot: no held milestone. Before v1.2.1-f2 this raised ZeroDivisionError."""
    res = {r.id: r for r in metrics.baseline_metrics(ad.build_context(ad.load(FIX / "v_snapshot")))}
    for mid in ("forms_over_interviews_held", "enrollments_over_interviews_held", "links_over_forms"):
        assert np.isnan(res[mid].value) and res[mid].denominator_value == 0, mid
    out = by_id(ad.evaluate(ad.load(FIX / "v_snapshot")))
    assert out["forms_over_interviews_held"]["reason"] == "HM"      # module absent takes precedence


def test_zero_denominator_with_history_is_den0():
    """Milestones exist but no held interview: ratios over held interviews are DEN0; the main KPI is a true 0."""
    def drop_held(t):
        se = t["stage_events"]
        t["stage_events"] = se[se.to_stage != "interview_held"].reset_index(drop=True)
    out = by_id(ad.evaluate(load_modified("v_milestone", drop_held)))
    for mid in ("forms_over_interviews_held", "enrollments_over_interviews_held", "followup_48h_manual_advisor"):
        assert out[mid] == {"id": mid, "status": "not_available", "reason": "DEN0", "missing": ["nonzero_denominator"]}, mid
    main = out["main_kpi_interviews_held_over_opportunities"]
    assert main["status"] == "available" and main["value"] == 0.0 and main["numerator_value"] == 0 and main["denominator_value"] == 8
    assert out["links_over_forms"]["status"] == "available"          # forms still exist: 2 / 2


def test_insufficient_data_is_insuf():
    """No mature enrollment: the sales-cycle statistics have no observation; enrollments / eligible is a true 0."""
    can = ad.load(FIX / "v_full")
    L, A = ad.to_frames(can)
    L["enrolled_at"] = pd.NaT
    ctx = metrics.build_context(L, A, pd.DataFrame(columns=["lead_id", "issue_type", "detail"]), ad.load_config())
    out = by_id(ad.evaluate_context(ctx, can))
    for mid in ("sales_cycle_median_days", "sales_cycle_mean_days"):
        assert out[mid] == {"id": mid, "status": "not_available", "reason": "INSUF", "missing": ["observations"]}, mid
    e = out["enrollments_over_eligible_leads"]
    assert e["status"] == "available" and e["value"] == 0.0 and e["denominator_value"] == 8


def test_no_appointment_from_the_personal_whatsapp_start():
    """Dataset without appointments scheduled from 2025-07-01. Before v1.2.1-f2 this raised AttributeError."""
    def drop_july(t):
        ap = t["appointments"]
        t["appointments"] = ap[ap.scheduled_for < "2025-07-01"].reset_index(drop=True)
    can = load_modified("v_full", drop_july)
    assert (can.typed["appointments"].scheduled_for < "2025-07-01").all()
    out = by_id(ad.evaluate(can))
    for mid in ("show_rate_with_personal_whatsapp", "show_rate_without_personal_whatsapp"):
        assert out[mid]["reason"] == "DEN0", mid
    full = by_id(ad.evaluate(ad.load(FIX / "v_full")))
    for mid in ("share_manual_route", "main_kpi_interviews_held_over_opportunities", "sla_first_attempt_24h_manual",
                "followup_48h_manual_advisor", "enrollments_over_eligible_leads", "sales_cycle_median_days"):
        assert out[mid] == full[mid], mid                            # unrelated metrics are unaffected
    # 47 - 2 personal-WhatsApp rates (DEN0) - 2 nurture rates (DEN0: the fixture has no nurture data)
    assert sum(e["status"] == "available" for e in out.values()) == 43


def test_no_appointment_table_at_all():
    """v_no_appointments. Before v1.2.1-f2 Context.bot_pre raised TypeError and showlead could not be averaged."""
    ctx = ad.build_context(ad.load(FIX / "v_no_appointments"))
    assert ctx.bot_pre["B"].first_appt.dtype.kind == "M"             # datetime kept, all NaT
    assert ctx.showlead.dtype == bool and len(ctx.showlead) == 0
    assert ctx.personal_wa_appointments.personal_wa.dtype == bool
    out = by_id(ad.evaluate(ad.load(FIX / "v_no_appointments")))
    for mid in ("show_rate_per_appointment", "cancellation_rate", "show_rate_per_lead", "bot_pre_interview_confirmation",
                "bot_pre_interview_human_contact", "show_rate_with_personal_whatsapp", "contact_rate"):
        assert out[mid]["reason"] == "APT", mid


def test_module_absent_is_never_reported_as_zero():
    """v_no_automated: metrics.py would compute SLA 0 / 6 (no manual attempt is visible); the adapter reports AUT."""
    res = {r.id: r for r in metrics.baseline_metrics(ad.build_context(ad.load(FIX / "v_no_automated")))}
    assert res["sla_first_attempt_24h_manual"].value == 0.0
    out = by_id(ad.evaluate(ad.load(FIX / "v_no_automated")))
    assert out["sla_first_attempt_24h_manual"] == {"id": "sla_first_attempt_24h_manual", "status": "not_available",
                                                   "reason": "AUT", "missing": ["is_automated"]}


def test_unavailable_metrics_do_not_block_the_others():
    out = ad.evaluate(ad.load(FIX / "v_snapshot"))
    cat = [e for e in out["catalogue"] if e["status"] == "available"]
    assert len(cat) == 16 and all(e["value"] is not None for e in cat)


def test_undefined_value_without_documented_reason_raises():
    with pytest.raises(ValueError):
        ad.undefined_reason("rate", float("nan"), 5)
    with pytest.raises(ValueError):
        ad.undefined_reason("count", None, 0)
    assert ad.undefined_reason("rate", 0.0, 5) is None
