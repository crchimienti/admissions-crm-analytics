"""Mapping of the generated admissions CSV files to the canonical schema and back (F2).

Mapeo de los CSV de admisiones generados al esquema canónico y vuelta al formato que lee metrics.py.

* The mapping is complete: every CSV column is mapped, recomputed (derived) or represented at dataset level.
* Nothing is inferred: stage events come only from the first-entry columns; history_mode is milestone_first_entry.
* Round trip: canonical -> adapter rebuilds leads.csv / activities.csv frames identical to checks.load (all
  columns and dtypes), including the derived fields recomputed with the F0 rules.
* Amounts: discount_amount aggregates the two discounts, which stay as adm_ attributes; the original price is
  reconstructed exactly for every enrollment.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import checks  # noqa: E402
from canonical import mapping  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import read_canonical, write_canonical  # noqa: E402
from canonical.validate import capabilities, validate  # noqa: E402


@pytest.fixture(scope="module")
def source():
    return mapping.read_source(ROOT / "data")


@pytest.fixture(scope="module")
def can(source):
    c = validate(mapping.map_admissions_csv(*source))
    ad.check_profile(c)
    return c


@pytest.fixture(scope="module")
def frames(can):
    return ad.to_frames(can)


@pytest.fixture(scope="module")
def loaded():
    return checks.load(ROOT / "data")


def test_every_source_column_is_accounted_for(source):
    m = mapping.load_mapping()
    leads, acts = source
    assert list(leads.columns) == m["required_columns"]["leads"] and list(acts.columns) == m["required_columns"]["activities"]
    covered = (set(m["records"].values()) | set(m["milestones"]) | set(m["attributes"]) | set(m["derived_not_mapped"])
               | set(m["dataset_level"]) | {"is_duplicate", "is_reactivation", "campaign_discount", "one_time_discount",
                                            "next_task_due_at"})
    assert set(leads.columns) <= covered, set(leads.columns) - covered
    ap, ac = m["appointments"], m["activities"]
    acov = (set(v for k, v in ap.items() if k not in ("extensions", "constants")) | set(ap["extensions"].values())
            | set(ap["constants"]) | set(v for k, v in ac.items() if k != "extensions") | set(ac["extensions"].values()))
    assert set(acts.columns) <= acov, set(acts.columns) - acov


def test_dataset_row(can):
    ds = can.dataset
    assert ds["history_mode"] == "milestone_first_entry" and ds["timestamp_mode"] == "naive_wall_clock"
    assert ds["data_origin"] == "synthetic" and ds["source_timezone"] == "Europe/Madrid"
    assert ds["snapshot_at"] == "2025-12-31 23:59:00" and ds["attribute_prefix"] == "adm"


def test_row_counts(can, source):
    leads, acts = source
    T = can.tables
    assert len(T["records"]) == len(leads) == 7945
    assert len(T["activities"]) + len(T["appointments"]) == len(acts) == 89426
    assert len(T["appointments"]) == (acts.activity_type == "interview").sum() == 5816
    assert T["records"].record_origin.value_counts().to_dict() == {
        "original": int(((leads.is_duplicate == "False") & (leads.is_reactivation == "False")).sum()),
        "duplicate": int((leads.is_duplicate == "True").sum()), "reactivation": int((leads.is_reactivation == "True").sum())}


def test_stage_events_are_only_first_entry_columns(can, source):
    """One milestone per non-null first-entry column; no event from current_stage, appointments or activities."""
    leads, _ = source
    m = mapping.load_mapping()
    se = can.tables["stage_events"]
    assert set(se.event_kind) == {"first_entry_milestone"} and (se.from_stage == "").all()
    assert len(se) == sum(int((leads[c] != "").sum()) for c in m["milestones"])
    for col, stage in m["milestones"].items():
        got = se[se.to_stage == stage].set_index("record_id").occurred_at
        exp = leads.set_index("lead_id")[col]
        assert got.sort_index().equals(exp[exp != ""].sort_index().rename("occurred_at")), stage
    assert capabilities(can)["stage_transitions"] is False


def test_round_trip_frames_equal_checks_load(frames, loaded):
    L, A = frames
    L0, A0, _ = loaded
    pd.testing.assert_frame_equal(L, L0)
    pd.testing.assert_frame_equal(A, A0)


@pytest.mark.parametrize("col", ["first_human_attempt_at", "first_connected_at", "has_open_task", "next_task_due_at",
                                 "reassigned_flag"])
def test_derived_fields_recomputed_with_f0_rules(frames, loaded, col):
    pd.testing.assert_series_equal(frames[0][col], loaded[0][col])


def test_attributes_are_prefixed_and_typed(can):
    a = can.tables["record_attributes"]
    assert a.attribute.str.startswith("adm_").all()
    assert set(a.value_type) <= {"string", "int", "float", "bool", "timestamp"}
    assert not (a.value == "").any()


def test_amounts_keep_aggregate_and_split(can, loaded):
    R = can.typed["records"].set_index("record_id")
    A = can.tables["record_attributes"].pivot(index="record_id", columns="attribute", values="value")
    won = R[R.list_amount.notna()]
    assert len(won) == loaded[0].list_price.notna().sum() > 0
    camp = pd.to_numeric(A.loc[won.index, "adm_campaign_discount"])
    one = pd.to_numeric(A.loc[won.index, "adm_one_time_discount"])
    cents = lambda s: (s * 100).round().astype("int64")
    assert (cents(camp) + cents(one) == cents(won.discount_amount)).all()
    assert (cents(won.net_amount) + cents(won.discount_amount) == cents(won.list_amount)).all()   # original price
    L0 = loaded[0].set_index("lead_id").loc[won.index]
    assert (cents(camp) == cents(L0.campaign_discount)).all() and (cents(one) == cents(L0.one_time_discount)).all()


def test_reactivation_parents_follow_profile_rule(can):
    R = can.tables["records"]
    rx = R[R.record_origin == "reactivation"]
    assert len(rx) > 0 and (rx.parent_record_id != "").all()
    assert (R[R.record_origin != "reactivation"].parent_record_id == "").all()


def test_mapping_is_deterministic(tmp_path, can, source):
    a, b = tmp_path / "a", tmp_path / "b"
    write_canonical(can, a)
    write_canonical(validate(mapping.map_admissions_csv(*source)), b)
    for p in sorted(a.iterdir()):
        assert p.read_bytes() == (b / p.name).read_bytes(), p.name
    back = validate(read_canonical(a))
    for t in can.tables:
        assert back.tables[t].equals(can.tables[t]), t
