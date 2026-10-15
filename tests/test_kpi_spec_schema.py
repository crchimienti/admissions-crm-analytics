"""kpi-spec/0.1 configuration validation (F3.0): the real configuration is valid and everything outside the closed
language is rejected with its K_* code, including the ratio contract.

Validación de la configuración kpi-spec/0.1: la configuración real es válida y todo lo que sale del lenguaje cerrado
se rechaza con su código K_*, incluido el contrato de los ratios.
"""
from __future__ import annotations

import pytest

from kpi_helpers import KPI_IDS, SPEC_PATH, raw_spec, spec_with
from kpispec.spec import KpiSpecError, load_schema, load_spec


def rejects(change, code):
    with pytest.raises(KpiSpecError) as e:
        spec_with(change)
    assert e.value.code == code, (e.value.code, e.value.detail)


def test_real_configuration_is_valid_and_has_the_eight_kpis():
    s = load_spec(SPEC_PATH)
    assert list(s.kpis) == KPI_IDS
    assert {k["op"] for k in s.kpis.values()} == {"count", "share", "ratio", "duration_stat"}
    assert s.population_unit("show_appointments") == "appointment" and s.population_unit("mature") == "lead"


def test_closed_lists_in_the_schema():
    sc = load_schema()
    assert list(sc["operations"]) == ["count", "share", "ratio", "duration_stat", "field_stat"]
    assert sorted(sc["filters"]) == sorted(["equals", "in", "not_null", "is_null", "age_at_least_days",
                                            "created_before_snapshot_minus_hours", "at_or_before_snapshot",
                                            "weekday_in", "duration_le_hours"])
    assert list(sc["ratio"]["relations"]) == ["subset_of", "same_base", "independent_allowed"]
    assert sorted(sc["not_available_reasons"]) == sorted(["FLD", "HM", "HF", "AUT", "APT", "DEN0", "INSUF", "ORD"])


@pytest.mark.parametrize("key", ["or", "expr", "formula", "code", "lambda", "eval", "python", "sql"])
def test_expression_like_keys_are_forbidden(key):
    rejects(lambda r: r["populations"]["eligible"].update({key: "x"}), "K_FORBIDDEN_KEY")


def test_top_level_and_versions():
    rejects(lambda r: r.update(extra=1), "K_UNKNOWN_KEY")
    rejects(lambda r: r.pop("fields"), "K_MISSING_KEY")
    rejects(lambda r: r.update(spec_version="kpi-spec/0.2"), "K_SPEC_VERSION")
    rejects(lambda r: r.update(time_model="utc"), "K_TIME_MODEL")      # UTC arrives with F3.5


def test_unknown_operation_filter_field_population():
    rejects(lambda r: r["kpis"]["eligible_leads"].update(op="sum"), "K_UNKNOWN_OP")
    rejects(lambda r: r["populations"]["eligible"]["where"].append({"between": ["created_at", 1, 2]}), "K_UNKNOWN_FILTER")
    rejects(lambda r: r["populations"]["eligible"]["where"].append({"equals": ["nope", 1]}), "K_UNKNOWN_FIELD")
    rejects(lambda r: r["kpis"]["eligible_leads"].update(population="nope"), "K_UNKNOWN_POPULATION")
    rejects(lambda r: r["populations"]["eligible"].update({"from": "mature"}), "K_MISSING_KEY")   # unit and from


def test_population_cycle_is_rejected():
    def cyc(r):
        r["populations"]["a"] = {"from": "b"}
        r["populations"]["b"] = {"from": "a"}
    rejects(cyc, "K_UNKNOWN_POPULATION")


def test_filter_arguments_and_units():
    rejects(lambda r: r["populations"]["eligible"]["where"].append({"weekday_in": ["created_at", [7]]}), "K_UNKNOWN_FILTER")
    rejects(lambda r: r["populations"]["eligible"]["where"].append({"equals": ["appt_outcome", "held"]}), "K_UNIT")
    rejects(lambda r: r["fields"]["created_at"].update(source="sql.created_at"), "K_FIELD_SOURCE")
    rejects(lambda r: r["fields"]["created_at"].pop("if_missing"), "K_MISSING_KEY")
    rejects(lambda r: r["fields"]["appt_outcome"].update(unit="lead"), "K_UNIT")


def test_describe_must_be_complete():
    rejects(lambda r: r["kpis"]["eligible_leads"]["describe"].pop("time_basis"), "K_MISSING_KEY")
    rejects(lambda r: r["kpis"]["eligible_leads"]["describe"].update(note="x"), "K_UNKNOWN_KEY")


def test_p90_needs_linear_interpolation():
    rejects(lambda r: r["kpis"]["first_response_p90_hours"].pop("interpolation"), "K_MISSING_KEY")


# ---- ratio contract ---------------------------------------------------------------------------------------------- #
def _ratio(**kw):
    def change(r):
        r["populations"]["mature_with_booking"] = {"from": "mature", "where": [{"not_null": "held_entered_at"}]}
        r["populations"]["booked_and_held"] = {"from": "mature_with_booking", "where": [{"not_null": "form_entered_at"}]}
        k = {"op": "ratio", "describe": dict(r["kpis"]["forms_over_interviews_held"]["describe"]), **kw}
        r["kpis"]["test_ratio"] = {key: v for key, v in k.items() if v is not None}
    return change


def test_valid_ratios():
    spec_with(_ratio(relation="same_base", numerator="mature_with_form", denominator="mature_with_held"))
    spec_with(_ratio(relation="subset_of", numerator="booked_and_held", denominator="mature_with_booking"))
    spec_with(_ratio(relation="independent_allowed", numerator="mature_with_form", denominator="eligible",
                     justification="illustration only"))


@pytest.mark.parametrize("kw,code", [
    (dict(relation="same_base", numerator="show_appointments", denominator="mature"), "K_RATIO_UNIT"),
    (dict(relation="subset_of", numerator="mature_with_form", denominator="mature_with_held"), "K_RATIO_RELATION"),
    (dict(relation="same_base", numerator="mature_with_form", denominator="eligible"), "K_RATIO_RELATION"),
    (dict(relation=None, numerator="mature_with_form", denominator="mature_with_held"), "K_RATIO_RELATION_MISSING"),
    (dict(relation="independent_allowed", numerator="mature_with_form", denominator="eligible"), "K_RATIO_JUSTIFICATION"),
    (dict(relation="conversion", numerator="mature_with_form", denominator="mature_with_held"), "K_RATIO_RELATION"),
], ids=["units", "subset_of_not_derived", "same_base_different_bases", "no_relation", "no_justification", "unknown"])
def test_invalid_ratios(kw, code):
    rejects(_ratio(**kw), code)


def test_forms_over_held_is_declared_same_base_not_subset():
    k = raw_spec()["kpis"]["forms_over_interviews_held"]
    assert k["relation"] == "same_base"
