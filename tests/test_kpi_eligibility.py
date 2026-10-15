"""Eligibility in F3: `record_origin = original` preserves the F0 definition for the admissions profile.

Elegibilidad en F3: `record_origin = original` conserva la definición de F0 en el perfil de admisiones.

F0: an eligible lead has is_duplicate = false and is_reactivation = false. The admissions mapping sets
record_origin = duplicate if is_duplicate, reactivation if is_reactivation, original otherwise, and rejects rows with
both flags. So for this profile: original  <=>  not duplicate and not reactivation. This is a profile rule (the
`eligible` population of profiles/admissions/kpis.yaml), not an engine rule. Checked on the generated data (F0
loader), on the canonical path (adapter frames) and on the fixture. An unknown or null origin is a data error and a
missing origin field is FLD: neither can enter `eligible` silently.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from kpi_helpers import FIX, ROOT, SPEC_PATH, evaluate, fixture
import checks
from canonical import mapping
from canonical.adapters import admissions as ad
from canonical.contract import CanonicalError, read_canonical
from canonical.validate import validate
from kpispec.engine import Engine
from kpispec.fields import KpiDataError
from kpispec.spec import load_spec


def eligible_ids(can) -> set:
    eng = Engine(load_spec(SPEC_PATH), can)
    m = eng.mask("eligible")
    return set(m.index[m])


@pytest.fixture(scope="module")
def generated():
    can = validate(mapping.map_directory(ROOT / "data"))
    ad.check_profile(can)
    return can


def test_equivalence_on_generated_data_with_the_f0_loader(generated):
    L, _, _ = checks.load(ROOT / "data")
    f0 = set(L.lead_id[~L.is_duplicate & ~L.is_reactivation])
    assert len(f0) == 7691 and eligible_ids(generated) == f0


def test_equivalence_on_the_canonical_path(generated):
    L, _ = ad.to_frames(generated)                                   # frames rebuilt from canonical tables
    assert eligible_ids(generated) == set(L.lead_id[~L.is_duplicate & ~L.is_reactivation])
    R = generated.tables["records"]
    src = mapping.read_source(ROOT / "data")[0].set_index("lead_id")
    flags = src.loc[R.record_id]
    both_false = ((flags.is_duplicate == "False") & (flags.is_reactivation == "False")).values
    assert ((R.record_origin == "original").values == both_false).all()
    assert not ((flags.is_duplicate == "True") & (flags.is_reactivation == "True")).any()


def test_equivalence_on_the_fixture():
    exp = json.loads((FIX / "expected.json").read_text(encoding="utf-8"))["populations"]["members"]["eligible"]
    can = fixture("v_full")
    assert eligible_ids(can) == set(exp)
    L, _ = ad.to_frames(can)
    assert set(L.lead_id[~L.is_duplicate & ~L.is_reactivation]) == set(exp)


def test_mapping_refuses_both_flags():
    leads, acts = mapping.read_source(ROOT / "tests" / "fixtures" / "mapping_errors" / "base")
    leads.loc[2, "is_duplicate"] = "True"                             # L3 is a reactivation
    with pytest.raises(CanonicalError) as e:
        mapping.map_admissions_csv(leads, acts)
    assert e.value.codes == {"M_ORIGIN_CONFLICT"}


def test_unknown_origin_is_rejected_by_contract_and_by_engine():
    can = read_canonical(FIX / "v_full")
    can.tables["records"].loc[0, "record_origin"] = "copy"
    with pytest.raises(CanonicalError) as e:
        validate(can)
    assert "E_ENUM" in e.value.codes

    def unknown(typed):
        typed["records"].loc[typed["records"].record_id == "F01", "record_origin"] = "copy"
    with pytest.raises(KpiDataError) as e:
        evaluate(fixture("v_full", change_typed=unknown))
    assert e.value.code == "K_FIELD_VALUE"


def test_null_origin_is_rejected_by_engine():
    def null(typed):
        typed["records"].loc[typed["records"].record_id == "F01", "record_origin"] = None
    with pytest.raises(KpiDataError) as e:
        evaluate(fixture("v_full", change_typed=null))
    assert e.value.code == "K_FIELD_VALUE"


def test_missing_origin_field_is_fld_never_eligible():
    def drop(typed):
        typed["records"] = typed["records"].drop(columns="record_origin")
    r = evaluate(fixture("v_full", change_typed=drop))
    for kid, res in r.items():
        assert res["status"] == "not_available" and res["reason"] == "FLD", kid
        assert "record_origin" in res["missing"] or "appt_record_origin" in res["missing"], kid
