"""Fields and capabilities each F3.0 KPI requires (F3.0).

Campos y capacidades que requiere cada KPI de F3.0.

* The fields read by each KPI (its own and those of every population it is defined from) are exactly the approved
  table; nothing is assumed to be available.
* The capability codes derived from those fields equal profiles/admissions/kpi_requirements.yaml (F2).
"""
from __future__ import annotations

from kpi_helpers import KPI_IDS, SPEC_PATH
from canonical import availability
from kpispec.engine import _kpi_fields
from kpispec.spec import load_spec

EXPECTED_FIELDS = {
    "eligible_leads": ["record_origin"],
    "share_manual_route": ["record_origin", "entry_route"],
    "main_kpi_interviews_held_over_opportunities": ["record_origin", "created_at", "snapshot_at", "held_entered_at"],
    "show_rate_per_appointment": ["appt_record_origin", "appt_replaced_by", "appt_scheduled_for", "snapshot_at", "appt_outcome"],
    "forms_over_interviews_held": ["record_origin", "created_at", "snapshot_at", "form_entered_at", "held_entered_at"],
    "sla_first_attempt_24h_manual_weekend": ["record_origin", "entry_route", "created_at", "snapshot_at", "first_human_attempt_at"],
    "first_response_p90_hours": ["record_origin", "entry_route", "created_at", "snapshot_at", "first_human_attempt_at"],
    "sales_cycle_median_days": ["record_origin", "created_at", "snapshot_at", "won_at"],
}
CODE_TO_REQUIREMENT = {"HM": "stage_milestones", "HF": "stage_transitions", "AUT": "is_automated", "APT": "appointments"}


def test_fields_per_kpi():
    spec = load_spec(SPEC_PATH)
    got = {kid: _kpi_fields(spec, spec.kpis[kid]) for kid in KPI_IDS}
    assert {k: sorted(v) for k, v in got.items()} == {k: sorted(v) for k, v in EXPECTED_FIELDS.items()}


def test_every_field_declares_how_it_can_be_missing():
    spec = load_spec(SPEC_PATH)
    for name, f in spec.fields.items():
        assert "if_missing" in f or "needs" in f, name


def test_capabilities_match_kpi_requirements():
    spec = load_spec(SPEC_PATH)
    req = availability.load_requirements()["requirements"]
    for kid in KPI_IDS:
        codes = set()
        for f in _kpi_fields(spec, spec.kpis[kid]):
            fd = spec.fields[f]
            codes |= {fd["if_missing"]} if "if_missing" in fd else set(fd["needs"].values())
        assert {CODE_TO_REQUIREMENT[c] for c in codes if c != "FLD"} == set(req[kid]), kid


# --- eligibility equivalence (admissions profile rule) ----------------------------------------------------- #
import json  # noqa: E402

import pytest  # noqa: E402

from kpi_helpers import FIX, VARIANTS, evaluate, fixture  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from kpispec.engine import Engine  # noqa: E402

EXPECTED_ELIGIBLE = set(json.loads((FIX / "expected.json").read_text(encoding="utf-8"))["populations"]["members"]["eligible"])


@pytest.mark.parametrize("variant", VARIANTS)
def test_eligible_equivalence_on_every_fixture_variant(variant):
    """record_origin = original  <=>  is_duplicate = false AND is_reactivation = false, on each of the five variants:
    the engine population, the F0-style flags rebuilt by the adapter and the hand-calculated members agree."""
    can = fixture(variant)
    m = Engine(load_spec(SPEC_PATH), can).mask("eligible")
    engine_ids = set(m.index[m])
    L, _ = ad.to_frames(can)
    f0_ids = set(L.lead_id[~L.is_duplicate & ~L.is_reactivation])
    R = can.typed["records"]
    assert engine_ids == f0_ids == EXPECTED_ELIGIBLE == set(R.record_id[R.record_origin == "original"])
    flags = L.set_index("lead_id").loc[R.record_id]
    assert ((R.record_origin == "original").values == (~flags.is_duplicate & ~flags.is_reactivation).values).all()
    assert not (flags.is_duplicate & flags.is_reactivation).any()


# --- missing fields give FLD or the capability reason -------------------------------------------------------- #
@pytest.mark.parametrize("variant", VARIANTS)
def test_each_required_field_missing_gives_its_declared_reason(variant):
    """Remove each required records column in turn: every KPI that reads it becomes not_available with FLD (alone
    or combined with the variant's capability reason) and lists it; the KPIs that do not read it are unchanged."""
    spec = load_spec(SPEC_PATH)
    base = evaluate(fixture(variant))
    columns = {"record_origin": ["record_origin", "appt_record_origin"], "entry_route": ["entry_route"],
               "created_at": ["created_at"], "won_at": ["won_at"]}
    for col, field_names in columns.items():
        def drop(typed, col=col):
            typed["records"] = typed["records"].drop(columns=col)
        r = evaluate(fixture(variant, change_typed=drop))
        for kid in KPI_IDS:
            reads = set(_kpi_fields(spec, spec.kpis[kid])) & set(field_names)
            if reads:
                assert r[kid]["status"] == "not_available" and "FLD" in r[kid]["reason"].split("+"), (variant, col, kid)
                assert reads <= set(r[kid]["missing"]), (variant, col, kid)
                assert not ({"value", "numerator", "denominator"} & set(r[kid])), (variant, col, kid)
            else:
                assert r[kid] == base[kid], (variant, col, kid)


def test_missing_capability_is_its_code_not_fld():
    expected = {"v_snapshot": "HM", "v_no_automated": "AUT", "v_no_appointments": "APT"}
    for variant, code in expected.items():
        reasons = {res["reason"] for res in evaluate(fixture(variant)).values() if res["status"] == "not_available"}
        assert reasons == {code}, variant


def test_null_value_in_one_row_is_not_fld():
    def one_null(typed):
        typed["records"].loc[typed["records"].record_id == "F01", "entry_route"] = None
    r = evaluate(fixture("v_full", change_typed=one_null))
    assert r["share_manual_route"]["status"] == "available"
