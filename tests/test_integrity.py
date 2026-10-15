"""Integrity tests for the synthetic dataset.  Run:  pytest -q

* Logic checks must have zero violations (a violation is a generator bug).
* Deliberate anomalies are detected, reported and matched with the ground truth.
* Mutation tests corrupt copies of the data to prove the checks can fail.
* Reproducibility: regenerating with the fixed seed yields identical files.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import checks  # noqa: E402
from generate_data import generate  # noqa: E402

DATA = ROOT / "data"


@pytest.fixture(scope="module")
def data():
    return checks.load(DATA)


@pytest.fixture(scope="module")
def results(data):
    ch = checks.Checker(*data)
    table = ch.run()
    return table, ch.warnings


def logic_names():
    table, _ = checks.run_checks(DATA)
    return list(table.loc[table.category == "logic", "check"])


@pytest.mark.parametrize("name", logic_names())
def test_logic_check_has_no_violations(results, name):
    table, _ = results
    row = table[(table.category == "logic") & (table.check == name)].iloc[0]
    assert row.violations == 0, f"{name}: {row.violations} violations, e.g. {row['sample']}"


def test_every_injected_anomaly_type_is_reconciled(results, data):
    """Each anomaly type is reported with injected / detectable / detected counts that add up."""
    table, warnings = results
    rep = table[table.category == "anomaly"].set_index("check")
    expected = {"missing_lost_reason", "open_without_task", "overdue_task", "empty_post_interview_fields",
                "duplicate", "untouched_manual", "stage_support_omitted", "stalled"}
    assert set(data[2].issue_type) == expected
    assert set(rep.index) == expected
    for issue, r in rep.iterrows():
        assert r.detected == r.detectable, issue                     # detection rule = ground truth (observable part)
        assert r.injected == r.detectable + r.not_detectable, issue  # every injected case is accounted for
    for w in warnings:  # rate drift from the scenario parameter is reported, not failed
        print("WARNING:", w)


def test_cohort_maturity_uses_full_timestamps():
    snap = pd.Timestamp("2025-12-31 23:59:00")
    thr = snap - pd.Timedelta(days=60)
    leads = pd.DataFrame({
        "lead_id": ["a", "b", "c", "d"], "is_duplicate": False, "is_reactivation": False, "snapshot_date": snap,
        "created_at": [pd.Timestamp("2025-10-31 23:59:59"), thr, thr + pd.Timedelta(seconds=1),
                       pd.Timestamp("2025-12-01 08:00")]})
    out = checks.cohort_maturity(leads)
    assert out.loc[pd.Period("2025-10", "M"), "label"] == "mature"     # 61 days old
    assert out.loc[pd.Period("2025-11", "M"), "mature_leads"] == 1      # exactly 60 x 24 h -> mature; +1 s -> not
    assert out.loc[pd.Period("2025-11", "M"), "label"] == "partial"
    assert out.loc[pd.Period("2025-12", "M"), "label"] == "immature"


def test_dataset_maturity_labels_match_lead_rule(data):
    leads = data[0]
    out = checks.cohort_maturity(leads)
    age_ok = (leads.snapshot_date - leads.created_at) >= pd.Timedelta(days=60)
    for period, row in out.iterrows():
        sel = (leads.created_at.dt.to_period("M") == period) & ~leads.is_duplicate & ~leads.is_reactivation
        assert row.mature_leads == age_ok[sel].sum()
        assert (row.label == "mature") == bool(age_ok[sel].all())


def test_followup_window_is_strictly_after_the_interview():
    snap = pd.Timestamp("2025-12-31 23:59:00")
    held = pd.Timestamp("2025-12-01 10:00:00")
    leads = pd.DataFrame({
        "lead_id": ["pre_only", "edge_48h", "late", "auto_only", "in_window", "window_open", "dup"],
        "is_duplicate": [False] * 6 + [True], "is_reactivation": False, "snapshot_date": snap,
        "entered_interview_held_at": [held] * 5 + [snap - pd.Timedelta(hours=10), held]})
    base = dict(actor_type="advisor", direction="outbound", activity_type="call", is_automated=False)
    acts = pd.DataFrame([
        {**base, "lead_id": "pre_only", "activity_at": held - pd.Timedelta(hours=2)},       # before the interview
        {**base, "lead_id": "pre_only", "activity_at": held},                              # at the interview: not after
        {**base, "lead_id": "edge_48h", "activity_at": held + pd.Timedelta(hours=48)},     # inclusive upper bound
        {**base, "lead_id": "late", "activity_at": held + pd.Timedelta(hours=48, seconds=1)},
        {**base, "lead_id": "auto_only", "activity_at": held + pd.Timedelta(hours=1), "is_automated": True},
        {**base, "lead_id": "in_window", "activity_at": held + pd.Timedelta(hours=5), "activity_type": "whatsapp"},
        {**base, "lead_id": "window_open", "activity_at": snap - pd.Timedelta(hours=5)},
        {**base, "lead_id": "dup", "activity_at": held + pd.Timedelta(hours=1)},
    ])
    r = checks.followup_within_48h(leads, acts)
    assert r["leads_with_follow_up"] == {"edge_48h", "in_window"}
    assert r["denominator"] == 5            # window_open (not complete) and dup (not eligible) are excluded
    assert r["numerator"] == 2


def test_followup_indicator_on_dataset_matches_row_level_recount(data):
    leads, acts, _ = data
    r = checks.followup_within_48h(leads, acts)
    held = leads.set_index("lead_id").entered_interview_held_at
    n = 0
    for lid in r["leads_with_follow_up"]:
        a = acts[(acts.lead_id == lid) & (acts.actor_type == "advisor") & (acts.direction == "outbound")
                 & acts.activity_type.isin(["call", "whatsapp"]) & ~acts.is_automated.astype(bool)]
        t0 = held[lid]
        assert ((a.activity_at > t0) & (a.activity_at <= t0 + pd.Timedelta(hours=48))).any(), lid
        n += 1
    assert n == r["numerator"] and 0 < r["numerator"] <= r["denominator"]


def test_regeneration_is_reproducible(tmp_path):
    """Same seed -> byte-identical CSV files."""
    leads, acts, gt = generate()
    for name, df in (("leads.csv", leads), ("activities.csv", acts), ("dq_ground_truth.csv", gt)):
        df.to_csv(tmp_path / name, index=False, lineterminator="\n")   # v1.4.2-gh: LF on every OS, as the generator
        assert (tmp_path / name).read_bytes() == (DATA / name).read_bytes(), name


def test_expected_workload_table_matches_formula():
    cfg = yaml.safe_load(open(ROOT / "config" / "simulation_params.yaml", encoding="utf-8"))
    w = cfg["team"]["assignment_weight"]
    advisors = cfg["team"]["advisors"]
    for doc in ("assumptions.md", "assumptions.es.md"):
        text = (ROOT / "docs" / doc).read_text(encoding="utf-8")
        rows = re.findall(r"^\| (600|620|640|680|780) \|[^|]*\|(.*)\|\s*$", text, flags=re.M)
        assert len(rows) == 5, doc
        for vol, rest in rows:
            cells = [c.strip().strip("*").replace(",", ".") for c in rest.split("|")]
            values, total = [float(c) for c in cells[:5]], float(cells[5])
            for adv, val in zip(advisors, values):
                assert abs(val - round(int(vol) * w[adv], 1)) < 1e-9, (doc, vol, adv)
            assert abs(total - int(vol)) < 1e-9
    months = {m for m, v in cfg["volume"]["monthly_new_eligible"].items()}
    assert months == set(range(1, 13))


# --------------------------------------------------------------------------- #
# Mutation tests: each corruption must be caught by at least one logic check
# --------------------------------------------------------------------------- #
def _violations(leads, acts, gt, pattern):
    table = checks.Checker(leads, acts, gt).run()
    hit = table[(table.category == "logic") & table.check.str.contains(pattern, regex=False)]
    assert len(hit), f"no check matching {pattern!r}"
    return int(hit.violations.sum())


def _copy(data):
    return tuple(d.copy() for d in data)


def test_mutation_pricing(data):
    L, A, G = _copy(data)
    i = L.index[L.pipeline_stage == "closed_won"][0]
    L.at[i, "net_price"] += 10
    assert _violations(L, A, G, "pricing formula") > 0


def test_mutation_stage_order(data):
    L, A, G = _copy(data)
    i = L.index[L.entered_form_completed_at.notna()][0]
    L.at[i, "entered_form_completed_at"] = L.at[i, "entered_interview_held_at"] - pd.Timedelta(days=1)
    assert _violations(L, A, G, "non-decreasing") > 0


def test_mutation_duplicate_flag(data):
    L, A, G = _copy(data)
    i = L.index[L.is_duplicate][0]
    L.at[i, "is_duplicate"] = False
    assert _violations(L, A, G, "14-day detection rule") > 0


def test_mutation_iloc_bd1_action(data):
    L, A, G = _copy(data)
    i = A.index[(A.sequence_name == "iloc") & (A.business_day_index == 2) & (A.activity_type == "call")][0]
    A.at[i, "business_day_index"] = 1
    assert _violations(L, A, G, "no BD1 action") > 0


def test_mutation_past_pending_appointment(data):
    L, A, G = _copy(data)
    i = A.index[(A.activity_type == "interview") & (A.interview_outcome == "held")][0]
    A.at[i, "interview_outcome"] = "pending"
    assert _violations(L, A, G, "pending <=> scheduled after the snapshot") > 0


def test_mutation_missing_reason_in_nurture(data):
    L, A, G = _copy(data)
    i = L.index[L.lead_status == "nurture"][0]
    L.at[i, "lost_reason"] = None
    assert _violations(L, A, G, "R3 exception scope") > 0


def test_mutation_orphan_activity(data):
    L, A, G = _copy(data)
    extra = A.iloc[[0]].copy()
    extra["activity_id"], extra["lead_id"] = "A9999999", "L999999"
    A = pd.concat([A, extra], ignore_index=True)
    assert _violations(L, A, G, "every activity belongs to a lead") > 0


def test_mutation_open_task_on_closed_lead(data):
    L, A, G = _copy(data)
    i = L.index[L.pipeline_stage == "closed_lost"][0]
    L.at[i, "has_open_task"] = True
    assert _violations(L, A, G, "has_open_task") > 0


def test_mutation_reactivation_person(data):
    L, A, G = _copy(data)
    i = L.index[L.is_reactivation][0]
    L.at[i, "person_key"] = "P999999"
    assert _violations(L, A, G, "reactivations link") > 0


def test_mutation_uninjected_anomaly(data):
    L, A, G = _copy(data)
    i = L.index[(L.pipeline_stage == "closed_lost") & L.lost_reason.isin(["financial"])][0]
    L.at[i, "lost_reason"] = None  # not in the ground truth -> logic error
    assert _violations(L, A, G, "missing_lost_reason: detected but not injected") > 0
