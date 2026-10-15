"""Shared helpers for the F3.0 KPI tests (not a test module)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import read_canonical  # noqa: E402
from canonical.validate import validate  # noqa: E402
from kpispec import engine  # noqa: E402
from kpispec.spec import load_spec, validate_spec  # noqa: E402

SPEC_PATH = ROOT / "profiles" / "admissions" / "kpis.yaml"
FIX = ROOT / "tests" / "fixtures" / "canonical_handcalc"
VARIANTS = ["v_full", "v_milestone", "v_snapshot", "v_no_automated", "v_no_appointments"]
KPI_IDS = ["eligible_leads", "share_manual_route", "main_kpi_interviews_held_over_opportunities",
           "show_rate_per_appointment", "forms_over_interviews_held", "sla_first_attempt_24h_manual_weekend",
           "first_response_p90_hours", "sales_cycle_median_days"]


def raw_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def spec_with(change) -> object:
    """The real configuration, changed in place by `change(raw)`, then validated."""
    raw = copy.deepcopy(raw_spec())
    change(raw)
    return validate_spec(raw)


def fixture(variant="v_full", change_tables=None, change_typed=None):
    """A fixture variant; change_tables edits the stored tables before validation, change_typed edits the typed
    tables after validation (to simulate a future load the current contract would not even accept)."""
    can = read_canonical(FIX / variant)
    if change_tables:
        change_tables(can.tables)
    can = validate(can)
    ad.check_profile(can)
    if change_typed:
        change_typed(can.typed)
    return can


def evaluate(can, spec=None) -> dict:
    return {r["id"]: r for r in engine.evaluate(spec or load_spec(SPEC_PATH), can)}
