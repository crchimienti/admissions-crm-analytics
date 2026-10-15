"""Timestamp policy (F2): naive wall clock only for synthetic / legacy data; real time zones normalised to UTC;
ambiguous and non-existent local times are errors.

Política de timestamps: reloj local ingenuo solo para datos sintéticos o legacy; zonas reales normalizadas a UTC;
horas ambiguas o inexistentes dan error.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical import mapping  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import CanonicalError, normalize_timestamps  # noqa: E402
from canonical.validate import validate  # noqa: E402

CASES = yaml.safe_load((ROOT / "tests" / "fixtures" / "timezones" / "cases.yaml").read_text(encoding="utf-8"))
TZ = CASES["source_timezone"]
BASE = ROOT / "tests" / "fixtures" / "mapping_errors" / "base"


@pytest.mark.parametrize("case", CASES["utc_ok"], ids=lambda c: c["why"])
def test_utc_normalisation(case):
    assert normalize_timestamps(pd.Series([case["in"]]), "utc", TZ, "t").iloc[0] == case["out"]


@pytest.mark.parametrize("case", CASES["utc_errors"], ids=lambda c: c["why"])
def test_utc_errors(case):
    with pytest.raises(CanonicalError) as e:
        normalize_timestamps(pd.Series([case["in"]]), "utc", TZ, "t")
    assert e.value.codes == {case["code"]}


@pytest.mark.parametrize("case", CASES["naive_ok"], ids=lambda c: c["why"])
def test_naive_kept_as_written(case):
    assert normalize_timestamps(pd.Series([case["in"]]), "naive_wall_clock", TZ, "t").iloc[0] == case["out"]


@pytest.mark.parametrize("case", CASES["naive_errors"], ids=lambda c: c["why"])
def test_naive_errors(case):
    with pytest.raises(CanonicalError) as e:
        normalize_timestamps(pd.Series([case["in"]]), "naive_wall_clock", TZ, "t")
    assert e.value.codes == {case["code"]}


def test_utc_needs_a_time_zone_for_naive_values():
    with pytest.raises(CanonicalError) as e:
        normalize_timestamps(pd.Series(["2025-07-01 12:00:00"]), "utc", None, "t")
    assert e.value.codes == {"M_NO_TIMEZONE"}


def test_naive_wall_clock_is_refused_for_real_data():
    leads, acts = mapping.read_source(BASE)
    with pytest.raises(CanonicalError) as e:
        mapping.map_admissions_csv(leads, acts, dataset_overrides={"data_origin": "real"})
    assert e.value.codes == {"M_NAIVE_NOT_ALLOWED"}


def test_utc_mode_dataset_is_valid_and_adapter_refuses_it():
    """A UTC dataset passes the contract; the admissions adapter declines it in F2 (wall-clock SLA definitions)."""
    leads, acts = mapping.read_source(BASE)
    can = validate(mapping.map_admissions_csv(leads, acts, dataset_overrides={"timestamp_mode": "utc"}))
    rec = can.tables["records"].set_index("record_id")
    assert rec.at["L1", "created_at"] == "2025-02-03T09:00:00Z"        # 10:00 Madrid (UTC+1) in February
    assert can.dataset["snapshot_at"] == "2025-06-30T21:59:00Z"        # 23:59 Madrid (UTC+2) in June
    ad.check_profile(can)
    with pytest.raises(CanonicalError) as e:
        ad.to_frames(can)
    assert e.value.codes == {"A_TIMESTAMP_MODE"}
