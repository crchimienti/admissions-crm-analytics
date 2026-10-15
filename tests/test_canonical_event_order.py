"""Event order and record outcome (v1.2.2-f2, crm-canonical/0.1.1).

Orden de eventos y resultado del registro.

* Simultaneous events: regressions, reopens, entry counts and first entries do not depend on any order (each
  transition / reopen carries its own from_stage and to_stage), so shuffling rows or renaming event ids changes
  nothing. time_in_stage depends on order: without seq it is reported not_available (ORD), never resolved by stage,
  event_id or file position; with seq it follows seq.
* seq rules C08: unique per record, consistent with occurred_at, only in crm-canonical/0.1.1 datasets.
* Outcome open / won / lost comes from current_stage, not from the operational current_status (e.g. nurture).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical import history, mapping  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import CanonicalError, read_canonical  # noqa: E402
from canonical.validate import validate  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "canonical_handcalc"
EXP = json.loads((FIX / "expected.json").read_text(encoding="utf-8"))["history_full_event_history"]
ORDER_FREE = ("first_entry", "entry_count", "regression_events", "regression_rate", "reopen_events", "reopen_rate")


def simultaneous(perm_seed: int, rename: bool, with_seq: list | None = None):
    """v_full with two pairs of simultaneous events, rows shuffled, optionally renamed ids and a seq column.

    F03: E14 (interview_held -> interview_booked, regression) and E15 (interview_booked -> interview_held) at the
    same instant. F05: E23 (reopen closed_lost -> opportunity) and E24 (opportunity -> closed_lost) at the same instant.
    """
    can = read_canonical(FIX / "v_full")
    se = can.tables["stage_events"]
    se.loc[se.event_id == "E15", "occurred_at"] = se.loc[se.event_id == "E14", "occurred_at"].iloc[0]
    se.loc[se.event_id == "E24", "occurred_at"] = se.loc[se.event_id == "E23", "occurred_at"].iloc[0]
    if with_seq is not None:
        can.tables["dataset"].loc[0, "schema_version"] = "crm-canonical/0.1.1"
        se["seq"] = with_seq
    se = se.sample(frac=1, random_state=perm_seed).reset_index(drop=True)
    if rename:   # ids in the opposite order, so an id-based tie-break would flip
        se["event_id"] = [f"Z{99 - i:02d}" for i in range(len(se))]
    can.tables["stage_events"] = se
    can = validate(can)
    ad.check_profile(can)
    return can


def seq_column(swap_f03=False, swap_f05=False):
    """seq numbers each record's events in file order of v_full (E-ids are in time order); optionally swap a pair."""
    se = read_canonical(FIX / "v_full").tables["stage_events"]
    seq = se.groupby("record_id").cumcount() + 1
    seq = seq.astype(str).tolist()
    idx = {e: i for i, e in enumerate(se.event_id)}
    for flag, a, b in ((swap_f03, "E14", "E15"), (swap_f05, "E23", "E24")):
        if flag:
            seq[idx[a]], seq[idx[b]] = seq[idx[b]], seq[idx[a]]
    return seq


def cat(can):
    return {e["id"]: e for e in ad.evaluate(can)["catalogue"]}


@pytest.mark.parametrize("perm_seed,rename", [(0, False), (1, True), (7, True)])
def test_order_free_indicators_do_not_depend_on_row_order_or_ids(perm_seed, rename):
    c = cat(simultaneous(perm_seed, rename))
    for i in ORDER_FREE:
        got = {k: c[i][k] for k in ("value", "numerator", "denominator") if k in EXP[i]}
        assert got == {k: EXP[i][k] for k in got}, i
    assert c["regression_rate"]["numerator"] == 1 and c["regression_rate"]["denominator"] == 25
    assert c["reopen_rate"]["numerator"] == 1 and c["reopen_rate"]["denominator"] == 4


def test_time_in_stage_is_indeterminate_without_seq():
    can = simultaneous(3, True)
    c = cat(can)
    assert c["time_in_stage"] == {"id": "time_in_stage", "status": "not_available", "reason": "ORD", "missing": ["event_order"]}
    with pytest.raises(history.OrderIndeterminateError) as e:
        T = can.typed
        history.time_in_stage(T["records"], T["stage_events"], "full_event_history", ad.load_rules(), T["dataset"].snapshot_at.iloc[0])
    assert e.value.records == ["F03", "F05"]


def test_time_in_stage_follows_seq_when_the_source_gives_it():
    a = cat(simultaneous(3, True, with_seq=seq_column()))
    b = cat(simultaneous(5, False, with_seq=seq_column(swap_f03=True)))
    assert a["time_in_stage"]["status"] == b["time_in_stage"]["status"] == "available"
    assert a["time_in_stage"]["value"] != b["time_in_stage"]["value"]          # the order comes from seq
    for i in ORDER_FREE:                                                        # order-free ones do not move
        assert {k: a[i].get(k) for k in ("value", "numerator", "denominator")} == \
               {k: b[i].get(k) for k in ("value", "numerator", "denominator")}, i


def test_no_ties_no_seq_is_determinate():
    c = cat(ad.load(FIX / "v_full"))
    assert c["time_in_stage"]["status"] == "available"


def test_seq_rules():
    with pytest.raises(CanonicalError) as e:
        simultaneous(0, False, with_seq=["1"] * 27)
    assert "E_SEQ" in e.value.codes
    with pytest.raises(CanonicalError) as e:            # E01 (02-03) after E02 in seq: contradicts timestamps
        s = seq_column(); s[0], s[1] = s[1], s[0]
        simultaneous(0, False, with_seq=s)
    assert "E_SEQ_ORDER" in e.value.codes
    can = read_canonical(FIX / "v_full")
    can.tables["stage_events"]["seq"] = seq_column()   # dataset still declares crm-canonical/0.1
    with pytest.raises(CanonicalError) as e:
        validate(can)
    assert "E_SCHEMA_VERSION" in e.value.codes


def test_outcome_comes_from_stage_not_from_operational_status():
    can = ad.load(FIX / "v_full")
    R = can.tables["records"].set_index("record_id")
    out = ad.record_outcome(R)
    assert R.at["F05", "current_status"] == "nurture" and out["F05"] == "lost"
    assert out[["F01", "F04"]].tolist() == ["won", "won"] and out["F02"] == "lost"
    assert (out[R.current_status.isin(["new", "working"])] == "open").all()


def test_outcome_on_generated_data():
    can = validate(mapping.map_directory(ROOT / "data"))
    R = can.tables["records"]
    out = ad.record_outcome(R)
    assert out.value_counts().to_dict() == {"lost": int((R.current_stage == "closed_lost").sum()),
                                            "won": int((R.current_stage == "closed_won").sum()),
                                            "open": int((~R.current_stage.isin(["closed_won", "closed_lost"])).sum())}
    nurture = R.current_status == "nurture"
    assert nurture.any() and (out[nurture] == "lost").all()                      # nurture is not a fourth outcome
    assert ((out == "won") == (R.won_at != "")).all() and ((out == "lost") == (R.lost_at != "")).all()
