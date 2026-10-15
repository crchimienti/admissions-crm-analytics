"""Contract crm-canonical/0.1: the validator accepts valid datasets and rejects each kind of violation (F2).

Contrato crm-canonical/0.1: el validador acepta datasets válidos y rechaza cada tipo de infracción.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import CanonicalError, read_canonical, write_canonical, load_contract, SCHEMA_VERSION  # noqa: E402
from canonical.validate import validate  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "canonical_handcalc"


def full():
    return read_canonical(FIX / "v_full")


def rejects(can, code):
    with pytest.raises(CanonicalError) as e:
        validate(can)
    assert code in e.value.codes, e.value.codes


def test_contract_file_declares_the_tables_modes_and_version():
    c = load_contract()
    assert c["schema_version"] == SCHEMA_VERSION == "crm-canonical/0.1.1"
    assert c["accepts_schema_versions"] == ["crm-canonical/0.1", "crm-canonical/0.1.1"]
    assert c["tables"]["stage_events"]["columns"]["seq"] == {"type": "int", "required": False, "nullable": False,
                                                             "since": "crm-canonical/0.1.1"}
    assert list(c["tables"]) == ["dataset", "records", "stage_events", "activities", "appointments", "record_attributes"]
    assert set(c["history_modes"]) == {"full_event_history", "milestone_first_entry", "snapshot_only"}
    assert c["history_modes"]["milestone_first_entry"]["allowed_event_kinds"] == ["first_entry_milestone"]
    assert c["history_modes"]["snapshot_only"]["allowed_event_kinds"] == []
    assert c["timestamp_modes"]["naive_wall_clock"]["allowed_data_origins"] == ["synthetic", "legacy"]


def test_contract_has_no_admissions_vocabulary():
    """Stages, routes, reasons and reactivation rules belong to the profile, not to the neutral contract."""
    text = (ROOT / "schema" / "canonical_v0.1.1.yaml").read_text(encoding="utf-8")
    body = text.split("\ntables:", 1)[1]
    for word in ("interview", "bot_booked", "future_intake", "enrollment", "iloc", "nurture", "adm_", "closed_won"):
        assert word not in body, word


@pytest.mark.parametrize("variant", ["v_full", "v_milestone", "v_snapshot", "v_no_automated", "v_no_appointments"])
def test_fixture_variants_are_valid(variant):
    can = validate(read_canonical(FIX / variant))
    ad.check_profile(can)


def test_contract_0_1_1_only_adds_seq_and_its_rules():
    """crm-canonical/0.1 is kept unchanged; 0.1.1 equals it except the seq column and rules C08-C09."""
    import yaml
    old = yaml.safe_load((ROOT / "schema" / "canonical_v0.1.yaml").read_text(encoding="utf-8"))
    new = load_contract()
    assert old["schema_version"] == "crm-canonical/0.1"
    cols = dict(new["tables"]["stage_events"]["columns"]); cols.pop("seq")
    assert cols == old["tables"]["stage_events"]["columns"]
    assert {k: v for k, v in new["tables"].items() if k != "stage_events"} == {k: v for k, v in old["tables"].items() if k != "stage_events"}
    assert new["history_modes"] == old["history_modes"] and new["timestamp_modes"] == old["timestamp_modes"]
    assert new["rules"][:7] == old["rules"] and [r["id"] for r in new["rules"][7:]] == ["C08", "C09"]


def test_write_read_round_trip(tmp_path):
    can = full()
    write_canonical(can, tmp_path)
    back = read_canonical(tmp_path)
    for t in can.tables:
        assert back.tables[t].equals(can.tables[t]), t


def test_schema_version_mismatch():
    can = full(); can.tables["dataset"].loc[0, "schema_version"] = "crm-canonical/0.2"
    rejects(can, "E_SCHEMA_VERSION")


def test_missing_required_table_and_column():
    can = full(); del can.tables["records"]
    rejects(can, "E_MISSING_TABLE")
    can = full(); can.tables["records"] = can.tables["records"].drop(columns="created_at")
    rejects(can, "E_MISSING_COLUMN")


def test_unknown_column_and_prefix_rules():
    can = full(); can.tables["records"]["campaign_discount"] = ""
    rejects(can, "E_UNKNOWN_COLUMN")
    can = full(); can.tables["record_attributes"].loc[0, "attribute"] = "campaign_discount"
    rejects(can, "E_ATTRIBUTE_PREFIX")
    can = full(); can.tables["stage_events"]["adm_note"] = ""   # no extensions on stage_events
    rejects(can, "E_UNKNOWN_COLUMN")


def test_null_type_enum_and_pattern():
    can = full(); can.tables["records"].loc[0, "created_at"] = ""
    rejects(can, "E_NULL")
    can = full(); can.tables["records"].loc[0, "list_amount"] = "abc"
    rejects(can, "E_TYPE")
    can = full(); can.tables["activities"].loc[0, "is_automated"] = "yes"
    rejects(can, "E_TYPE")
    can = full(); can.tables["records"].loc[0, "record_origin"] = "copy"
    rejects(can, "E_ENUM")
    can = full(); can.tables["dataset"].loc[0, "currency"] = "euro"
    rejects(can, "E_PATTERN")
    can = full(); can.tables["record_attributes"].loc[0, "value"] = "six hundred"
    rejects(can, "E_TYPE")


def test_timestamp_must_follow_mode():
    can = full(); can.tables["activities"].loc[0, "occurred_at"] = "2025-02-03T10:02:00Z"
    rejects(can, "E_TIMESTAMP_FORMAT")


def test_naive_wall_clock_only_for_synthetic_or_legacy():
    can = full(); can.tables["dataset"].loc[0, "data_origin"] = "real"
    rejects(can, "E_NAIVE_NOT_ALLOWED")
    can = full(); can.tables["dataset"].loc[0, "data_origin"] = "legacy"
    validate(can)


def test_keys():
    can = full(); can.tables["activities"].loc[1, "activity_id"] = "A001"
    rejects(can, "E_PK_DUPLICATE")
    can = full(); can.tables["appointments"].loc[0, "record_id"] = "F99"
    rejects(can, "E_FK")
    can = full(); can.tables["records"].loc[11, "parent_record_id"] = "F99"
    rejects(can, "E_FK")


def test_event_kind_must_match_history_mode():
    can = full(); can.tables["dataset"].loc[0, "history_mode"] = "milestone_first_entry"
    rejects(can, "E_EVENT_KIND")
    can = read_canonical(FIX / "v_milestone"); can.tables["dataset"].loc[0, "history_mode"] = "full_event_history"
    rejects(can, "E_EVENT_KIND")
    can = full(); can.tables["dataset"].loc[0, "history_mode"] = "snapshot_only"
    rejects(can, "E_EVENT_KIND")


def test_one_milestone_per_record_and_stage_and_from_stage_rules():
    can = read_canonical(FIX / "v_milestone")
    se = can.tables["stage_events"]
    dup = se.iloc[[0]].copy(); dup["event_id"] = "M99"
    can.tables["stage_events"] = __import__("pandas").concat([se, dup], ignore_index=True)
    rejects(can, "E_MILESTONE_DUP")
    can = read_canonical(FIX / "v_milestone"); can.tables["stage_events"].loc[0, "from_stage"] = "new_lead"
    rejects(can, "E_FROM_STAGE")
    can = full(); can.tables["stage_events"].loc[0, "from_stage"] = ""
    rejects(can, "E_FROM_STAGE")


def test_nothing_after_the_snapshot():
    can = full(); can.tables["stage_events"].loc[0, "occurred_at"] = "2025-08-01 10:00:00"
    rejects(can, "E_AFTER_SNAPSHOT")


def test_reschedule_chain_and_capability_consistency():
    can = full(); can.tables["appointments"].loc[4, "rescheduled_from_appointment_id"] = ""
    rejects(can, "E_RESCHEDULE_CHAIN")
    can = full(); can.tables["appointments"] = can.tables["appointments"].drop(columns="booking_is_automated")
    rejects(can, "E_CAPABILITY_MISMATCH")


def test_f2_code_has_no_network_crm_or_new_dependency():
    import ast
    forbidden = {"requests", "urllib", "http", "socket", "httpx", "aiohttp", "hubspot", "simple_salesforce", "jsonschema",
                 "pydantic", "pandera", "streamlit", "flask", "fastapi"}
    files = sorted((ROOT / "src" / "canonical").rglob("*.py")) + [ROOT / "scripts" / "map_to_canonical.py", ROOT / "scripts" / "f2_run.py"]
    for p in files:
        mods = set()
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module.split(".")[0])
        assert not mods & forbidden, (p.name, mods & forbidden)
        assert mods <= {"__future__", "argparse", "hashlib", "importlib", "json", "platform", "re", "shutil", "subprocess",
                        "sys", "time", "datetime", "pathlib", "dataclasses", "zoneinfo", "itertools", "numpy", "pandas",
                        "yaml", "metrics", "canonical", "src"}, (p.name, mods)


def test_profile_rules_are_separate_from_the_contract():
    """A dataset can be contract-valid and still break an admissions rule (here: discount split)."""
    can = full()
    a = can.tables["record_attributes"]
    a.loc[(a.record_id == "F01") & (a.attribute == "adm_one_time_discount"), "value"] = "300.0"
    validate(can)
    with pytest.raises(CanonicalError) as e:
        ad.check_profile(can)
    assert e.value.codes == {"P_DISCOUNT_SPLIT"}
    can = full(); can.tables["records"].loc[11, "parent_record_id"] = ""
    validate(can)                                    # the neutral contract does not require a parent
    with pytest.raises(CanonicalError) as e:
        ad.check_profile(can)
    assert "P_REACTIVATION_PARENT_MISSING" in e.value.codes
