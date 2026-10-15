"""F0 baseline tests: the metrics exported by the notebook (baseline/metrics_v1.json) are recomputed here
independently, directly from the CSV files with plain pandas, without importing the notebook's code.

Pruebas de la línea base F0: las métricas exportadas por el notebook se recalculan aquí de forma independiente
a partir de los CSV.

Run after `python scripts/build_notebook.py` (which writes the JSON).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "baseline" / "metrics_v1.json"
H48, D60 = pd.Timedelta(hours=48), pd.Timedelta(days=60)
REQUIRED = ["id", "label_en", "label_es", "unit", "kind", "population", "numerator", "denominator",
            "time_basis", "definition_ref", "numerator_value", "denominator_value", "value"]


@pytest.fixture(scope="module")
def base():
    if not BASELINE.exists():
        pytest.fail("baseline/metrics_v1.json missing: run `python scripts/build_notebook.py` first")
    return json.loads(BASELINE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ref():
    """Independent recomputation of every baseline metric: id -> (value, numerator, denominator)."""
    L = pd.read_csv(ROOT / "data" / "leads.csv")
    A = pd.read_csv(ROOT / "data" / "activities.csv")
    for c in [c for c in L.columns if c.endswith("_at") or c == "snapshot_date"]:
        L[c] = pd.to_datetime(L[c])
    for c in ("activity_at", "interview_scheduled_for", "task_due_at"):
        A[c] = pd.to_datetime(A[c])
    cfg = yaml.safe_load((ROOT / "config" / "simulation_params.yaml").read_text(encoding="utf-8"))
    snap = L.snapshot_date.iloc[0]
    r = {}

    def rate(mid, num_mask_or_n, den_n):
        n = int(num_mask_or_n.sum()) if hasattr(num_mask_or_n, "sum") else int(num_mask_or_n)
        r[mid] = (n / den_n, n, int(den_n))

    E = L[(L.is_duplicate == False) & (L.is_reactivation == False)].copy()  # noqa: E712
    EM = E[(snap - E.created_at) >= D60]
    held = EM.entered_interview_held_at.notna()
    r["eligible_leads"] = (len(E), len(E), None)
    r["mature_eligible_leads"] = (len(EM), len(EM), None)
    r["duplicate_rows"] = (int(L.is_duplicate.sum()),) * 2 + (None,)
    r["reactivation_rows"] = (int(L.is_reactivation.sum()),) * 2 + (None,)
    rate("share_manual_route", E.entry_path == "manual", len(E))
    rate("main_kpi_interviews_held_over_opportunities", held, len(EM))
    for route, mid in (("manual", "held_rate_manual_route"), ("bot_booked", "held_rate_bot_route")):
        sub = EM[EM.entry_path == route]
        rate(mid, sub.entered_interview_held_at.notna(), len(sub))
    rate("booking_rate", EM.entered_interview_booked_at.notna(), len(EM))

    # appointments: eligible lead, not replaced, slot <= snapshot
    I = A[(A.activity_type == "interview") & A.lead_id.isin(E.lead_id) & A.replaced_by_activity_id.isna()
          & (A.interview_scheduled_for <= snap)].merge(E[["lead_id", "entry_path", "created_at"]], on="lead_id")
    S = I[I.interview_outcome.isin(["held", "no_show"])]
    rate("show_rate_per_appointment", S.interview_outcome == "held", len(S))
    for route, mid in (("manual", "show_rate_per_appointment_manual"), ("bot_booked", "show_rate_per_appointment_bot")):
        s = S[S.entry_path == route]
        rate(mid, s.interview_outcome == "held", len(s))
    SM = S[(snap - S.created_at) >= D60]
    per_lead = SM.groupby("lead_id").interview_outcome.apply(lambda x: (x == "held").any())
    rate("show_rate_per_lead", per_lead, len(per_lead))
    rate("cancellation_rate", I.interview_outcome == "cancelled", len(I))

    form = EM.entered_form_completed_at.notna()
    rate("forms_over_interviews_held", form, held.sum())
    rate("enrollments_over_interviews_held", EM.enrolled_at.notna(), held.sum())
    rate("links_over_forms", EM.entered_enrollment_link_sent_at.notna(), form.sum())
    rate("enrollments_over_eligible_leads", EM.enrolled_at.notna(), len(EM))
    cyc = ((EM.enrolled_at - EM.created_at).dt.total_seconds() / 86400).dropna()
    r["sales_cycle_median_days"] = (cyc.median(), None, len(cyc))
    r["sales_cycle_mean_days"] = (cyc.mean(), None, len(cyc))

    M = E[E.entry_path == "manual"]
    Mw = M[M.created_at <= snap - pd.Timedelta(hours=24)]
    resp = (Mw.first_human_attempt_at - Mw.created_at).dt.total_seconds() / 3600
    rate("sla_first_attempt_24h_manual", resp <= 24, len(Mw))
    wk = Mw.created_at.dt.weekday >= 5
    rate("sla_first_attempt_24h_manual_weekday", resp[~wk] <= 24, (~wk).sum())
    rate("sla_first_attempt_24h_manual_weekend", resp[wk] <= 24, wk.sum())
    rate("sla_first_attempt_same_day_manual", Mw.first_human_attempt_at.dt.date == Mw.created_at.dt.date, len(Mw))
    r["first_response_median_hours"] = (resp.median(), None, int(resp.notna().sum()))
    r["first_response_p90_hours"] = (resp.quantile(0.9), None, int(resp.notna().sum()))
    att = E.first_human_attempt_at.notna()
    rate("contact_rate", E.first_connected_at[att].notna(), att.sum())
    rate("reassignment_rate_manual", M.reassigned_flag == True, len(M))  # noqa: E712

    B = E[E.entry_path == "bot_booked"]
    first_slot = (A[A.activity_type == "interview"].sort_values(["activity_at", "activity_id"])
                  .groupby("lead_id").interview_scheduled_for.first())
    pre = A[A.lead_id.isin(B.lead_id)].assign(slot=lambda d: d.lead_id.map(first_slot))
    pre = pre[pre.activity_at < pre.slot]
    rate("bot_pre_interview_confirmation",
         pre[(pre.sequence_name == "pre_interview_reminder") & (pre.actor_type == "bot")].lead_id.nunique(), len(B))
    rate("bot_pre_interview_human_contact",
         pre[(pre.actor_type == "advisor") & (pre.is_automated == False)].lead_id.nunique(), len(B))  # noqa: E712

    # follow-up: strictly after the first held interview, up to +48 h; window complete before the snapshot
    HW = E[E.entered_interview_held_at.notna() & (E.entered_interview_held_at + H48 <= snap)]
    adv = A[(A.actor_type == "advisor") & (A.direction == "outbound") & A.activity_type.isin(["call", "whatsapp"])
            & (A.is_automated == False)].merge(HW[["lead_id", "entered_interview_held_at"]], on="lead_id")  # noqa: E712
    ok = (adv.activity_at > adv.entered_interview_held_at) & (adv.activity_at <= adv.entered_interview_held_at + H48)
    rate("followup_48h_manual_advisor", adv.lead_id[ok].nunique(), len(HW))

    OP = E[~E.pipeline_stage.isin(["closed_won", "closed_lost"])]
    r["open_leads_at_snapshot"] = (len(OP), len(OP), None)
    rate("open_without_next_task", OP.has_open_task == False, len(OP))  # noqa: E712
    overdue = set(A.lead_id[(A.activity_type == "task") & (A.task_status == "overdue")])
    rate("open_with_overdue_task", OP.lead_id.isin(overdue), len(OP))
    lost = E[E.pipeline_stage == "closed_lost"]
    rate("closed_lost_without_reason", lost.lost_reason.isna(), len(lost))
    lr = lost[lost.lost_reason.notna()]
    rate("lost_reason_share_iloc", lr.lost_reason == "iloc", len(lr))

    work = E.groupby([E.first_owner_id, E.created_at.dt.month]).size()
    r["advisor_months_over_150_realised"] = (int((work > 150).sum()), int((work > 150).sum()), int(work.size))
    vol, w = cfg["volume"]["monthly_new_eligible"], cfg["team"]["assignment_weight"]
    exp = [vol[m] * w[a] for a in w for m in range(1, 13)]
    r["advisor_months_over_150_expected"] = (sum(x > 150 for x in exp),) * 2 + (len(exp),)

    W = E[E.enrolled_at.notna()]
    r["enrollments_total"] = (len(W), len(W), None)
    r["avg_net_price_eur"] = (W.net_price.mean(), None, len(W))
    for pt, mid in (("single", "avg_net_price_single_eur"), ("installments", "avg_net_price_installments_eur")):
        r[mid] = (W.loc[W.payment_type == pt, "net_price"].mean(), None, int((W.payment_type == pt).sum()))
    rate("installments_share", W.payment_type == "installments", len(W))
    NU = E[E.nurture_started_at.notna() & (E.nurture_started_at <= snap - pd.Timedelta(days=150))]
    rate("nurture_reactivation_complete_window", NU.nurture_end_reason == "reactivated", len(NU))
    nr = A[A.sequence_name == "nurture"]
    rate("nurture_email_failure_rate", nr.email_status.isin(["not_sent", "failed"]), len(nr))

    pw = A[A.sequence_step == "personal_whatsapp"][["lead_id", "activity_at"]]
    S2 = S[S.interview_scheduled_for >= "2025-07-01"].merge(pw, on="lead_id", how="left", suffixes=("", "_pw"))
    S2["pw_before"] = S2.activity_at_pw < S2.interview_scheduled_for
    flag = S2.groupby("activity_id").agg(pw=("pw_before", "any"), held=("interview_outcome", lambda x: x.iloc[0] == "held"))
    for has, mid in ((True, "show_rate_with_personal_whatsapp"), (False, "show_rate_without_personal_whatsapp")):
        sub = flag[flag.pw == has]
        rate(mid, sub.held, len(sub))
    return r


def test_baseline_metadata_and_input_hashes(base):
    assert base["baseline_id"] == "v1.0.0-f0" and base["seed"] == 42
    for path, digest in base["inputs_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, f"{path} changed since the baseline"
    assert base["logic_checks"]["violations"] == 0


def test_every_metric_is_fully_described(base):
    ids = [m["id"] for m in base["metrics"]]
    assert len(ids) == len(set(ids))
    for m in base["metrics"]:
        missing = [k for k in REQUIRED if k not in m]
        assert not missing, (m.get("id"), missing)
        for k in ("label_en", "label_es", "unit", "kind", "population", "numerator", "time_basis"):
            assert str(m[k]).strip(), (m["id"], k)
        assert m["kind"] in {"count", "rate", "mean", "median", "p90"}
        assert m["unit"] in {"lead", "appointment", "deal", "advisor_month", "email"}
        if m["kind"] == "rate":
            assert m["denominator"] and m["denominator_value"], m["id"]
            assert abs(m["value"] - m["numerator_value"] / m["denominator_value"]) < 1e-6, m["id"]
        for ref_path in m["definition_ref"]:
            assert (ROOT / ref_path.split(" §")[0]).exists(), ref_path


def test_every_metric_matches_independent_recomputation(base, ref):
    assert {m["id"] for m in base["metrics"]} == set(ref), "metric ids differ from the independent recomputation"
    for m in base["metrics"]:
        value, num, den = ref[m["id"]]
        assert abs(m["value"] - round(float(value), 6)) < 1e-9, (m["id"], m["value"], value)
        if num is not None:
            assert m["numerator_value"] == num, (m["id"], m["numerator_value"], num)
        if den is not None:
            assert m["denominator_value"] == den, (m["id"], m["denominator_value"], den)


def test_cohort_maturity_section_matches_lead_rule(base):
    L = pd.read_csv(ROOT / "data" / "leads.csv", parse_dates=["created_at", "snapshot_date"])
    E = L[~L.is_duplicate & ~L.is_reactivation]
    mature = (E.snapshot_date - E.created_at) >= D60
    for c in base["cohort_maturity"]:
        sel = E.created_at.dt.to_period("M").astype(str) == c["cohort"]
        assert c["eligible_leads"] == sel.sum() and c["mature_leads"] == mature[sel].sum()
        exp = "mature" if mature[sel].all() else ("immature" if not mature[sel].any() else "partial")
        assert c["label"] == exp, c["cohort"]


def test_readme_key_figures_come_from_the_baseline(base):
    """Each headline figure in both READMEs is the baseline value, formatted per language."""
    v = {m["id"]: m for m in base["metrics"]}
    en, es = (ROOT / "README.md").read_text(encoding="utf-8"), (ROOT / "README.es.md").read_text(encoding="utf-8")
    pct_en = lambda x: f"{x * 100:.1f} %"
    pct_es = lambda x: f"{x * 100:.1f} %".replace(".", ",")
    for mid in ("main_kpi_interviews_held_over_opportunities", "held_rate_manual_route", "held_rate_bot_route",
                "show_rate_per_appointment", "show_rate_per_lead", "forms_over_interviews_held",
                "enrollments_over_interviews_held", "sla_first_attempt_24h_manual",
                "sla_first_attempt_24h_manual_weekday", "sla_first_attempt_24h_manual_weekend",
                "followup_48h_manual_advisor"):
        assert pct_en(v[mid]["value"]) in en, (mid, pct_en(v[mid]["value"]))
        assert pct_es(v[mid]["value"]) in es, (mid, pct_es(v[mid]["value"]))
    fu = v["followup_48h_manual_advisor"]
    assert f"{fu['numerator_value']:,} / {fu['denominator_value']:,}" in en
    assert f"{fu['numerator_value']:,} / {fu['denominator_value']:,}".replace(",", ".") in es
    for mid in ("eligible_leads", "mature_eligible_leads"):
        assert f"{v[mid]['value']:,}" in en and f"{v[mid]['value']:,}".replace(",", ".") in es
    price = round(v["avg_net_price_eur"]["value"])
    assert f"€{price:,}" in en and f"{price:,}".replace(",", ".") + " €" in es
    adv = v["advisor_months_over_150_realised"]["value"], v["advisor_months_over_150_expected"]["value"]
    assert re.search(rf"\| {adv[0]} / {adv[1]} \|", en) and re.search(rf"\| {adv[0]} / {adv[1]} \|", es)


@pytest.mark.parametrize("field,delta", [("value", 0.001), ("numerator_value", 1), ("denominator_value", -1)])
def test_altered_baseline_is_rejected(base, ref, field, delta):
    import copy
    bad = copy.deepcopy(base)
    m = next(x for x in bad["metrics"] if x["id"] == "main_kpi_interviews_held_over_opportunities")
    m[field] = m[field] + delta
    with pytest.raises(AssertionError):
        test_every_metric_matches_independent_recomputation(bad, ref)
