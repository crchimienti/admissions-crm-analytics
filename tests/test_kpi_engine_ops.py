"""KPI engine operations and unavailability (F3.0).

Operaciones del motor y no disponibilidad.

Cases kept apart: true zero (available 0), zero denominator (DEN0), no observation (INSUF), capability absent (HM,
HF, AUT, APT) and field not provided (FLD), with combined reasons and the exact list of missing fields. A
not_available result never carries value, numerator or denominator, and never blocks the other KPIs.
"""
from __future__ import annotations

import pandas as pd
import pytest

from kpi_helpers import KPI_IDS, evaluate, fixture, spec_with


def na(result):
    assert set(result) == {"id", "status", "reason", "missing"} and result["status"] == "not_available", result
    return result["reason"], result["missing"]


def test_operations_on_the_full_fixture():
    r = evaluate(fixture("v_full"))
    assert (r["eligible_leads"]["value"], r["eligible_leads"]["numerator"], r["eligible_leads"]["denominator"]) == (10, 10, None)
    assert (r["share_manual_route"]["numerator"], r["share_manual_route"]["denominator"]) == (7, 10)
    assert (r["forms_over_interviews_held"]["numerator"], r["forms_over_interviews_held"]["denominator"]) == (2, 4)
    assert r["first_response_p90_hours"]["value"] == 54.5 and r["first_response_p90_hours"]["numerator"] is None
    assert r["first_response_p90_hours"]["denominator"] == 6
    assert round(r["sales_cycle_median_days"]["value"], 6) == 8.291667 and r["sales_cycle_median_days"]["denominator"] == 2


def test_true_zero_is_an_available_zero():
    s = spec_with(lambda raw: raw["kpis"]["share_manual_route"].update(numerator_where=[{"equals": ["entry_route", "phone"]}]))
    r = evaluate(fixture("v_full"), s)["share_manual_route"]
    assert r == {"id": "share_manual_route", "status": "available", "value": 0.0, "numerator": 0, "denominator": 10}


def test_zero_denominator_is_den0():
    def empty_pop(raw):
        raw["populations"]["eligible"]["where"].append({"equals": ["entry_route", "phone"]})
    r = evaluate(fixture("v_full"), spec_with(empty_pop))
    assert na(r["share_manual_route"]) == ("DEN0", ["nonzero_denominator"])
    assert na(r["forms_over_interviews_held"]) == ("DEN0", ["nonzero_denominator"])
    assert r["eligible_leads"]["value"] == 0                          # a count of an empty population is a true 0


def test_no_observation_is_insuf():
    def no_wins(typed):
        typed["records"]["won_at"] = pd.NaT
    r = evaluate(fixture("v_full", change_typed=no_wins))
    assert na(r["sales_cycle_median_days"]) == ("INSUF", ["observations"])
    assert r["main_kpi_interviews_held_over_opportunities"]["status"] == "available"


@pytest.mark.parametrize("variant,expected", [
    ("v_snapshot", {"main_kpi_interviews_held_over_opportunities": ("HM", ["held_entered_at"]),
                    "forms_over_interviews_held": ("HM", ["form_entered_at", "held_entered_at"])}),
    ("v_no_automated", {"sla_first_attempt_24h_manual_weekend": ("AUT", ["first_human_attempt_at"]),
                        "first_response_p90_hours": ("AUT", ["first_human_attempt_at"])}),
    ("v_no_appointments", {"show_rate_per_appointment": ("APT", ["appt_record_origin", "appt_replaced_by",
                                                                 "appt_scheduled_for", "appt_outcome"])}),
])
def test_capability_absent(variant, expected):
    r = evaluate(fixture(variant))
    for kid, exp in expected.items():
        assert na(r[kid]) == exp, kid
    assert sum(x["status"] == "available" for x in r.values()) == 8 - len(expected)   # the others are computed


def test_field_not_provided_is_fld_and_combines():
    def drop_route(typed):
        typed["records"] = typed["records"].drop(columns="entry_route")
    r = evaluate(fixture("v_full", change_typed=drop_route))
    assert na(r["share_manual_route"]) == ("FLD", ["entry_route"])
    assert na(r["first_response_p90_hours"]) == ("FLD", ["entry_route"])
    assert r["main_kpi_interviews_held_over_opportunities"]["status"] == "available"
    r = evaluate(fixture("v_no_automated", change_typed=drop_route))
    assert na(r["sla_first_attempt_24h_manual_weekend"]) == ("FLD+AUT", ["entry_route", "first_human_attempt_at"])


def test_profile_field_needs_are_checked_one_by_one():
    def drop_direction(typed):
        typed["activities"] = typed["activities"].drop(columns="direction")
    r = evaluate(fixture("v_full", change_typed=drop_direction))
    assert na(r["first_response_p90_hours"]) == ("FLD", ["first_human_attempt_at"])
    r = evaluate(fixture("v_no_automated", change_typed=drop_direction))
    assert na(r["first_response_p90_hours"]) == ("AUT+FLD", ["first_human_attempt_at"])


def test_appointment_field_without_column_is_fld():
    def drop_outcome(typed):
        typed["appointments"] = typed["appointments"].drop(columns="outcome")
    r = evaluate(fixture("v_full", change_typed=drop_outcome))
    assert na(r["show_rate_per_appointment"]) == ("FLD", ["appt_outcome"])


def test_duration_filter_null_end_never_matches_and_stays_in_the_denominator():
    """All eligible leads, attempt within 24 h of creation: F01 2 h, F05 20 h, F07 5 h, F08 16 h -> 4 / 10
    (F09 and F10 have no attempt: they do not match and stay in the denominator)."""
    s = spec_with(lambda raw: raw["kpis"]["share_manual_route"].update(
        numerator_where=[{"duration_le_hours": ["created_at", "first_human_attempt_at", 24]}]))
    r = evaluate(fixture("v_full"), s)["share_manual_route"]
    assert (r["numerator"], r["denominator"]) == (4, 10)


def test_weekend_filter():
    r = evaluate(fixture("v_full"))["sla_first_attempt_24h_manual_weekend"]
    assert (r["numerator"], r["denominator"]) == (1, 2)               # F02 (46 h) and F07 (5 h), Saturdays


def test_every_result_has_the_documented_shape():
    for v in ("v_full", "v_snapshot", "v_no_automated", "v_no_appointments"):
        for r in evaluate(fixture(v)).values():
            if r["status"] == "available":
                assert set(r) == {"id", "status", "value", "numerator", "denominator"}
            else:
                na(r)
    assert list(evaluate(fixture("v_full"))) == KPI_IDS


def _with_full_history_field(raw):
    raw["fields"]["held_entered_at_full"] = {"source": "stage_first_entry.interview_held", "unit": "lead", "if_missing": "HF"}
    raw["kpis"]["held_share_full_history"] = {
        "op": "share", "population": "eligible", "numerator_where": [{"not_null": "held_entered_at_full"}],
        "describe": dict(raw["kpis"]["share_manual_route"]["describe"])}


@pytest.mark.parametrize("variant,expected", [
    ("v_full", (4, 10)), ("v_milestone", ("HF", ["held_entered_at_full"])), ("v_snapshot", ("HF", ["held_entered_at_full"]))])
def test_full_history_field_is_hf_without_transitions(variant, expected):
    """A stage field declared if_missing: HF needs full history (milestones are not enough)."""
    r = evaluate(fixture(variant), spec_with(_with_full_history_field))["held_share_full_history"]
    if isinstance(expected[0], int):
        assert (r["status"], r["numerator"], r["denominator"]) == ("available", *expected)
    else:
        assert na(r) == expected


def test_hm_and_fld_combine_deterministically():
    def drop_created(typed):
        typed["records"] = typed["records"].drop(columns="created_at")
    r = evaluate(fixture("v_snapshot", change_typed=drop_created))
    assert na(r["main_kpi_interviews_held_over_opportunities"]) == ("FLD+HM", ["created_at", "held_entered_at"])
    assert na(r["forms_over_interviews_held"]) == ("FLD+HM", ["created_at", "form_entered_at", "held_entered_at"])


def test_ord_is_never_produced_by_the_order_free_f3_kpis():
    """Simultaneous stage events (no seq) leave the eight KPIs unchanged: none of them depends on event order."""
    def simultaneous(tables):
        se = tables["stage_events"]
        se.loc[se.event_id == "E15", "occurred_at"] = se.loc[se.event_id == "E14", "occurred_at"].iloc[0]
        se.loc[se.event_id == "E24", "occurred_at"] = se.loc[se.event_id == "E23", "occurred_at"].iloc[0]
        tables["stage_events"] = se.sample(frac=1, random_state=3).reset_index(drop=True)
    a, b = evaluate(fixture("v_full")), evaluate(fixture("v_full", change_tables=simultaneous))
    assert a == b and not any(r.get("reason") == "ORD" for r in b.values())
