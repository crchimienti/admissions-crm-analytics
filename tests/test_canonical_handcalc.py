"""Hand-calculated canonical fixture: five variants of one 12-record synthetic dataset (official F2 fixture since v1.2.1-f2).

Fixture canónico calculado a mano: cinco variantes de un mismo dataset sintético de 12 registros.

Three independent checks against tests/fixtures/canonical_handcalc/expected.json (values calculated by hand):
  A. expected-schema: every variant lists the 31 catalogue ids exactly once (available xor not_available), with
     capabilities_without_expected_value inside `available`; not_available entries carry only id and reason.
  B. independent: a small re-implementation in this file (plain pandas over the CSV files; it uses neither the
     generator, nor the adapter, nor src/metrics.py, nor src/canonical/history.py) reproduces the expected values.
  C. full path: canonical files -> validate -> admissions profile -> adapter -> src/metrics.py (+ history) reproduces
     the expected values and the availability matrix of all five variants (no variant skipped since v1.2.1-f2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical import availability, history  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import read_canonical  # noqa: E402
from canonical.validate import capabilities, validate  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "canonical_handcalc"
EXP = json.loads((FIX / "expected.json").read_text(encoding="utf-8"))
VARIANTS = list(EXP["variants"])
CATALOGUE = availability.catalogue()


def reference_values() -> dict:
    ref = {**EXP["metrics_all_eligible"], **EXP["metrics_mature_eligible"], **EXP["history_full_event_history"]}
    return {k: {f: v[f] for f in ("value", "numerator", "denominator") if f in v} for k, v in ref.items()}


def r6(v):
    if isinstance(v, dict):
        return {k: r6(x) for k, x in v.items()}
    return None if v is None else round(float(v), 6) if isinstance(v, float) else v


# --------------------------------------------------------------------------- #
# A. expected.json schema
# --------------------------------------------------------------------------- #
def test_catalogue_has_31_unique_ids():
    assert len(CATALOGUE) == 31 and len(set(CATALOGUE)) == 31


@pytest.mark.parametrize("variant", VARIANTS)
def test_expected_variant_covers_31_ids_exactly_once(variant):
    v = EXP["variants"][variant]
    av, na = v["available"], [e["id"] for e in v["not_available"]]
    assert len(av) == len(set(av)) and len(na) == len(set(na))
    assert not set(av) & set(na)
    assert sorted(av + na) == sorted(CATALOGUE)
    assert set(v["capabilities_without_expected_value"]) <= set(av)
    for e in v["not_available"]:
        assert set(e) == {"id", "reason"} and e["reason"] in {"HM", "HF", "AUT", "APT"}


def test_expected_variant_counts():
    counts = {k: (len(v["available"]), len(v["not_available"])) for k, v in EXP["variants"].items()}
    assert counts == {"v_full": (31, 0), "v_milestone": (25, 6), "v_snapshot": (16, 15),
                      "v_no_automated": (23, 8), "v_no_appointments": (25, 6)}


def test_every_available_id_has_a_reference_value_or_is_a_capability():
    ref = reference_values()
    for name, v in EXP["variants"].items():
        for i in v["available"]:
            assert i in ref or i in v["capabilities_without_expected_value"], (name, i)


def test_variants_differ_from_v_full_only_as_declared():
    """Same records, attributes and (where present) activities/appointments; only the declared removals differ."""
    full = read_canonical(FIX / "v_full").tables
    for name in VARIANTS:
        t = read_canonical(FIX / name).tables
        assert sorted(t) == sorted(EXP["variants"][name]["tables"]), name
        for tab in ("records", "record_attributes"):
            pd.testing.assert_frame_equal(t[tab], full[tab])
        acts, ap = full["activities"], full.get("appointments")
        if name == "v_no_automated":
            acts = acts.drop(columns="is_automated"); ap = ap.drop(columns="booking_is_automated")
        pd.testing.assert_frame_equal(t["activities"], acts)
        if "appointments" in t:
            pd.testing.assert_frame_equal(t["appointments"], ap)
        ds = t["dataset"].iloc[0]
        assert ds.history_mode == EXP["variants"][name]["history_mode"]
    assert (read_canonical(FIX / "v_no_automated").tables["stage_events"]
            .equals(full["stage_events"]))


# --------------------------------------------------------------------------- #
# B. independent recomputation (no generator, no adapter, no metrics.py, no history.py)
# --------------------------------------------------------------------------- #
def _read(name):
    d = FIX / name
    t = {p.stem: pd.read_csv(p, dtype=str, keep_default_na=False) for p in d.glob("*.csv")}
    for df in t.values():
        for c in df.columns:
            if c.endswith("_at") or c in ("scheduled_for",):
                df[c] = pd.to_datetime(df[c].replace("", None))
    return t


def independent(name) -> dict:
    t = _read(name)
    ds = t["dataset"].iloc[0]
    snap = ds.snapshot_at
    R = t["records"]
    E = R[R.record_origin == "original"].set_index("record_id")
    mature = E.index[(snap - E.created_at) >= pd.Timedelta(days=60)]
    out = {}
    frac = lambda n, d: {"value": n / d, "numerator": n, "denominator": d}
    manual = E.index[E.entry_route == "manual"]
    out["share_manual_route"] = frac(len(manual), len(E))
    acts = t["activities"]
    has_auto = "is_automated" in acts.columns
    ap = t.get("appointments")
    if ap is not None:
        ie = ap[ap.record_id.isin(E.index) & (ap.replaced_by_appointment_id == "") & (ap.scheduled_for <= snap)]
        show = ie[ie.outcome.isin(["held", "no_show"])]
        route = show.record_id.map(E.entry_route)
        out["show_rate_per_appointment"] = frac(int((show.outcome == "held").sum()), len(show))
        out["show_rate_per_appointment_manual"] = frac(int((show[route == "manual"].outcome == "held").sum()), int((route == "manual").sum()))
        out["show_rate_per_appointment_bot"] = frac(int((show[route == "bot_booked"].outcome == "held").sum()), int((route == "bot_booked").sum()))
        out["cancellation_rate"] = frac(int((ie.outcome == "cancelled").sum()), len(ie))
        sm = show[show.record_id.isin(mature)]
        per_lead = sm.groupby("record_id").outcome.apply(lambda s: (s == "held").any())
        out["show_rate_per_lead"] = frac(int(per_lead.sum()), len(per_lead))
    if has_auto:
        man = acts[(acts.actor_type == "advisor") & (acts.direction == "outbound") & acts.activity_type.isin(["call", "whatsapp"])
                   & (acts.is_automated == "False")]
        first = man.groupby("record_id").occurred_at.min()
        win = E.loc[manual][E.loc[manual].created_at <= snap - pd.Timedelta(hours=24)]
        h = (win.index.map(first).to_series(index=win.index) - win.created_at).dt.total_seconds() / 3600
        wk = win.created_at.dt.weekday >= 5
        out["sla_first_attempt_24h_manual"] = frac(int((h <= 24).sum()), len(win))
        out["sla_first_attempt_24h_manual_weekday"] = frac(int((h[~wk] <= 24).sum()), int((~wk).sum()))
        out["sla_first_attempt_24h_manual_weekend"] = frac(int((h[wk] <= 24).sum()), int(wk.sum()))
        same = win.index.map(first).to_series(index=win.index).dt.date == win.created_at.dt.date
        out["sla_first_attempt_same_day_manual"] = frac(int(same.sum()), len(win))
        hs = sorted(h.dropna())
        out["first_response_median_hours"] = {"value": float(np.median(hs)), "numerator": None, "denominator": len(hs)}
        pos = 0.9 * (len(hs) - 1); lo = int(pos)
        out["first_response_p90_hours"] = {"value": hs[lo] + (pos - lo) * (hs[lo + 1] - hs[lo]), "numerator": None, "denominator": len(hs)}
        if ap is not None:
            conn = pd.concat([acts.loc[(acts.activity_type == "call") & (acts.call_outcome == "connected"), ["record_id", "occurred_at"]],
                              acts.loc[acts.direction == "inbound", ["record_id", "occurred_at"]],
                              ap.loc[ap.outcome == "held", ["record_id", "scheduled_for"]].rename(columns={"scheduled_for": "occurred_at"})])
            connected = set(conn.record_id)
            attempted = [r for r in E.index if r in first.index]
            out["contact_rate"] = frac(sum(r in connected for r in attempted), len(attempted))
    se = t.get("stage_events")
    hmode = ds.history_mode
    if se is not None and hmode != "snapshot_only":
        kinds = ["first_entry_milestone"] if hmode == "milestone_first_entry" else ["transition", "reopen"]
        ent = se[se.event_kind.isin(kinds)].groupby(["record_id", "to_stage"]).occurred_at.min()
        entered = lambda stage: {r for (r, s) in ent.index if s == stage}
        M = list(mature)
        held, booked, form, link = (entered(s) & set(M) for s in ("interview_held", "interview_booked", "form_completed", "enrollment_link_sent"))
        won = set(E.index[E.won_at.notna()]) & set(M)
        Mm, Mb = [r for r in M if E.entry_route[r] == "manual"], [r for r in M if E.entry_route[r] == "bot_booked"]
        out["main_kpi_interviews_held_over_opportunities"] = frac(len(held), len(M))
        out["held_rate_manual_route"] = frac(len(held & set(Mm)), len(Mm))
        out["held_rate_bot_route"] = frac(len(held & set(Mb)), len(Mb))
        out["booking_rate"] = frac(len(booked), len(M))
        out["forms_over_interviews_held"] = frac(len(form), len(held))
        out["enrollments_over_interviews_held"] = frac(len(won), len(held))
        out["links_over_forms"] = frac(len(link), len(form))
        if has_auto:
            held_at = {r: ent[(r, "interview_held")] for r in E.index if (r, "interview_held") in ent.index}
            fw = [r for r, t0 in held_at.items() if t0 + pd.Timedelta(hours=48) <= snap]
            hit = [r for r in fw if ((man.record_id == r) & (man.occurred_at > held_at[r])
                                     & (man.occurred_at <= held_at[r] + pd.Timedelta(hours=48))).any()]
            out["followup_48h_manual_advisor"] = frac(len(hit), len(fw))
        stages = ["opportunity", "interview_booked", "interview_held", "form_completed", "enrollment_link_sent", "closed_won", "closed_lost"]
        ev = se[se.record_id.isin(E.index)]
        out["first_entry"] = {"value": {s: len(entered(s) & set(E.index)) for s in stages}}
        if hmode == "full_event_history":
            moves = ev[ev.event_kind.isin(["transition", "reopen"])]
            out["entry_count"] = {"value": {s: int((moves.to_stage == s).sum()) for s in stages}}
            order = {s: i for i, s in enumerate(["new_lead"] + stages[:5])}
            tr = ev[ev.event_kind == "transition"]
            back = tr[tr.from_stage.isin(order) & tr.to_stage.isin(order) & (tr.to_stage.map(order) < tr.from_stage.map(order))]
            out["regression_events"] = {"value": len(back)}
            out["regression_rate"] = frac(len(back), len(tr))
            term = set(moves.record_id[moves.to_stage.isin(["closed_won", "closed_lost"])])
            ro = ev[ev.event_kind == "reopen"]
            out["reopen_events"] = {"value": len(ro)}
            out["reopen_rate"] = frac(len(set(ro.record_id) & term), len(term))
    wonE = E.loc[mature][E.loc[mature].won_at.notna()]
    out["enrollments_over_eligible_leads"] = frac(len(wonE), len(mature))
    cyc = ((wonE.won_at - wonE.created_at).dt.total_seconds() / 86400).tolist()
    out["sales_cycle_median_days"] = {"value": float(np.median(cyc)), "numerator": None, "denominator": len(cyc)}
    out["sales_cycle_mean_days"] = {"value": float(np.mean(cyc)), "numerator": None, "denominator": len(cyc)}
    return out


@pytest.mark.parametrize("variant", VARIANTS)
def test_independent_recomputation_matches_hand_values(variant):
    ref = reference_values()
    got = independent(variant)
    v = EXP["variants"][variant]
    computable = [i for i in v["available"] if i not in v["capabilities_without_expected_value"]]
    assert sorted(got) == sorted(computable), (variant, sorted(set(got) ^ set(computable)))
    for i in computable:
        assert r6(got[i]) == r6(ref[i]), (variant, i, got[i], ref[i])


def test_independent_populations_match():
    t = _read("v_full")
    R = t["records"]; snap = t["dataset"].snapshot_at.iloc[0]
    E = R[R.record_origin == "original"]
    p = EXP["populations"]
    assert (len(R), len(E), (R.record_origin == "duplicate").sum(), (R.record_origin == "reactivation").sum()) == \
           (p["records"], p["eligible"], p["duplicates"], p["reactivations"])
    assert sorted(E.record_id[(snap - E.created_at) >= pd.Timedelta(days=60)]) == p["members"]["mature_eligible"]
    assert sorted(E.record_id[~E.current_stage.isin(["closed_won", "closed_lost"])]) == p["members"]["open_at_snapshot"]
    se = t["stage_events"]
    assert int(se[se.record_id.isin(E.record_id)].event_kind.eq("transition").sum()) == p["transition_events"]


# --------------------------------------------------------------------------- #
# C. full path: canonical -> adapter -> src/metrics.py (+ history.py)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module", params=VARIANTS)
def loaded(request):
    return request.param, ad.load(FIX / request.param)


def test_full_path_availability_matrix(loaded):
    name, can = loaded
    exp = EXP["variants"][name]
    st = ad.catalogue_availability(can)
    assert [s["id"] for s in st] == CATALOGUE
    assert [s["id"] for s in st if s["status"] == "available"] == [i for i in CATALOGUE if i in exp["available"]]
    assert [{"id": s["id"], "reason": s["reason"]} for s in st if s["status"] == "not_available"] == \
           sorted(exp["not_available"], key=lambda e: CATALOGUE.index(e["id"]))
    caps = capabilities(can)
    assert {k: caps[k] for k in exp["capabilities"]} == exp["capabilities"]


def _check_values(name, out):
    ref = reference_values()
    exp = EXP["variants"][name]
    cat = {e["id"]: e for e in out["catalogue"]}
    assert list(cat) == CATALOGUE
    for i in exp["available"]:
        e = cat[i]
        assert e["status"] == "available", (name, i)
        if i in exp["capabilities_without_expected_value"]:
            assert e.get("value") is not None, (name, i)
            continue
        got = {f: e.get(f) for f in ref[i]}
        assert r6(got) == r6(ref[i]), (name, i, got, ref[i])
    for n in exp["not_available"]:
        e = cat[n["id"]]
        assert e == {"id": n["id"], "status": "not_available", "reason": n["reason"], "missing": e["missing"]}
    availability.check_no_leak(out["catalogue"] + out["baseline_metrics"])


@pytest.mark.parametrize("name", VARIANTS)
def test_full_path_values_through_metrics_py(name):
    """Every available value of every variant, through the adapter and src/metrics.py (no variant is skipped)."""
    _check_values(name, ad.evaluate(ad.load(FIX / name)))


@pytest.mark.parametrize("name", VARIANTS)
def test_full_path_catalogue_has_no_computed_unavailability(name):
    """In the fixture every catalogue KPI is decided by capabilities only: no DEN0 / INSUF in the catalogue."""
    out = ad.evaluate(ad.load(FIX / name))
    assert not [e for e in out["catalogue"] if e.get("reason") in ("DEN0", "INSUF")]


def test_followup_window_boundaries():
    """Exactly +48 h is inside the window, +48 h 1 s is outside (calendar hours, inclusive upper bound)."""
    import metrics
    can = ad.load(FIX / "v_full")
    ctx = ad.build_context(can)
    fu = metrics.checks.followup_within_48h(ctx.raw_leads, ctx.A)
    assert fu["leads_with_follow_up"] == {"F01", "F03", "F04"} and fu["denominator"] == 4
    acts = can.typed["activities"].set_index("activity_id")
    held = ctx.raw_leads.set_index("lead_id").entered_interview_held_at
    assert acts.at["A031", "occurred_at"] - held["F04"] == pd.Timedelta(hours=48)
    assert acts.at["A032", "occurred_at"] - held["F02"] == pd.Timedelta(hours=48, seconds=1)


def test_coverage_inventory_points_to_existing_rows():
    cov = EXP["coverage"]
    t = read_canonical(FIX / "v_full").tables
    ids = set(t["records"].record_id) | set(t["activities"].activity_id) | set(t["appointments"].appointment_id) | set(t["stage_events"].event_id)
    import re
    for case, items in cov.items():
        for item in items:
            for token in re.findall(r"\b(?:F\d\d|A\d{3}|AP\d\d|E\d\d)\b", item):
                assert token in ids, (case, token)
    assert {"followup_exactly_48h", "followup_48h_plus_1s", "duplicate", "reactivation", "no_show", "reschedule",
            "cancellation", "human_activity_before_interview", "human_activity_after_interview", "re_entry",
            "regression", "reopen", "history_modes", "capability_absent"} <= set(cov)


def test_history_values_and_refusals():
    ref = EXP["history_full_event_history"]
    rules = ad.load_rules()
    full = ad.load(FIX / "v_full")
    h = ad.history_indicators(full)
    assert h["first_entry"]["value"] == ref["first_entry"]["value"]
    assert h["entry_count"]["value"] == ref["entry_count"]["value"]
    ms = ad.load(FIX / "v_milestone")
    T = ms.typed
    assert history.first_entry(T["records"], T["stage_events"], "milestone_first_entry", rules) == ref["first_entry"]["value"]
    for f in (history.entry_count, history.regressions, history.reopens):
        with pytest.raises(history.HistoryModeError):
            f(T["records"], T["stage_events"], "milestone_first_entry", rules)
    assert set(ad.history_indicators(ms)) == {"first_entry"}
    sn = ad.load(FIX / "v_snapshot")
    assert ad.history_indicators(sn) == {}
    with pytest.raises(history.HistoryModeError):
        history.first_entry(sn.typed["records"], T["stage_events"].iloc[:0], "snapshot_only", rules)


def test_milestone_mode_keeps_event_kind_and_counts_nothing_else():
    ms = ad.load(FIX / "v_milestone")
    se = ms.tables["stage_events"]
    assert set(se.event_kind) == {"first_entry_milestone"} and (se.from_stage == "").all()
    assert not se.duplicated(["record_id", "to_stage"]).any()


def test_no_inference_in_snapshot_only():
    """No milestone is derived from current_stage, appointments or activities when there is no stage history."""
    sn = ad.load(FIX / "v_snapshot")
    L, _ = ad.to_frames(sn)
    for col in ad.MILESTONE_COLUMNS.values():
        assert L[col].isna().all(), col
    # the state at the snapshot is still read as state (won_at / lost_at), not as history
    assert L.enrolled_at.notna().sum() == 2 and L.closed_lost_at.notna().sum() == 2


def test_milestones_do_not_depend_on_current_stage():
    """Changing current_stage (and nothing else) does not move any entered_*_at column."""
    full = ad.load(FIX / "v_full")
    L1, _ = ad.to_frames(full)
    can = read_canonical(FIX / "v_full")
    can.tables["records"].loc[can.tables["records"].record_id == "F07", "current_stage"] = "form_completed"
    validate(can)
    L2, _ = ad.to_frames(can)
    cols = list(ad.MILESTONE_COLUMNS.values())
    pd.testing.assert_frame_equal(L1[cols], L2[cols])


def test_derived_fields_match_hand_values():
    L, _ = ad.to_frames(ad.load(FIX / "v_full"))
    L = L.set_index("lead_id")
    for field in ("first_human_attempt_at", "first_connected_at"):
        for rid, exp in EXP["derived"][field].items():
            got = L.at[rid, field]
            assert (pd.isna(got) and exp is None) or str(got) == exp["at"], (field, rid, got, exp)
    for rid, exp in EXP["derived"]["entered_interview_held_at"].items():
        assert str(L.at[rid, "entered_interview_held_at"]) == exp["at"]
    Lm, _ = ad.to_frames(ad.load(FIX / "v_milestone"))
    pd.testing.assert_series_equal(Lm.entered_interview_held_at, L.reset_index().entered_interview_held_at)


def test_amount_reconstruction_is_exact():
    can = ad.load(FIX / "v_full")
    R = can.typed["records"].set_index("record_id")
    A = can.tables["record_attributes"].pivot(index="record_id", columns="attribute", values="value")
    for rid, exp in EXP["amount_reconstruction"].items():
        disc = float(A.at[rid, "adm_campaign_discount"]) + float(A.at[rid, "adm_one_time_discount"])
        assert disc == R.at[rid, "discount_amount"] == exp["discount_amount"]
        assert R.at[rid, "net_amount"] + disc == exp["original_price_reconstructed"] == R.at[rid, "list_amount"]
        assert A.at[rid, "adm_payment_type"] == exp["adm_payment_type"]
    L, _ = ad.to_frames(can)
    L = L.set_index("lead_id")
    assert L.loc[["F01", "F04"], "campaign_discount"].tolist() == [600.0, 500.0]
    assert L.loc[["F01", "F04"], "one_time_discount"].tolist() == [390.0, 0.0]
