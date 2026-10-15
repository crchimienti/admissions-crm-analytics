"""Mapping-error fixture (F2): each corrupted copy of a valid mini CSV pair fails with its expected code and at the
expected stage (mapping, contract or profile).

Fixture de errores de mapeo: cada copia corrompida falla con su código y en la etapa esperada.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical import mapping  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import CanonicalError  # noqa: E402
from canonical.validate import validate  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "mapping_errors"
CASES = yaml.safe_load((FIX / "cases.yaml").read_text(encoding="utf-8"))["cases"]


def run_pipeline(leads, acts, overrides=None):
    stage = "mapping"
    can = mapping.map_admissions_csv(leads, acts, dataset_overrides=overrides)
    stage = "contract"
    validate(can)
    stage = "profile"
    ad.check_profile(can)
    return can, stage


def test_base_is_valid():
    can, _ = run_pipeline(*mapping.read_source(FIX / "base"))
    L, A = ad.to_frames(can)
    assert len(L) == 3 and len(A) == 4


def test_at_least_ten_cases_with_unique_ids():
    assert len(CASES) >= 10 and len({c["id"] for c in CASES}) == len(CASES)
    assert {c["stage"] for c in CASES} == {"mapping", "contract", "profile"}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_mapping_error_case(case):
    leads, acts = mapping.read_source(FIX / "base")
    ch, overrides = case["change"], None
    if "set" in ch:
        s = ch["set"]
        df = leads if s["file"] == "leads" else acts
        assert s["column"] in df.columns and s["row"] < len(df)
        df.loc[s["row"], s["column"]] = s["value"]
    elif "drop_column" in ch:
        s = ch["drop_column"]
        (leads if s["file"] == "leads" else acts).drop(columns=s["column"], inplace=True)
    else:
        overrides = ch["dataset"]
    stage = "mapping"
    with pytest.raises(CanonicalError) as e:
        can = mapping.map_admissions_csv(leads, acts, dataset_overrides=overrides)
        stage = "contract"
        validate(can)
        stage = "profile"
        ad.check_profile(can)
    assert case["code"] in e.value.codes, e.value.codes
    assert stage == case["stage"]
