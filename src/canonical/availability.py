"""KPI availability for a canonical dataset (F2).

Disponibilidad de KPIs para un dataset canónico.

Each KPI lists its requirements in profiles/<profile>/kpi_requirements.yaml. The dataset's capabilities are read
from the data (history_mode, presence of activities.is_automated, presence of the appointments table); nothing is
inferred. A KPI with an unmet requirement is reported as

    {"id": ..., "status": "not_available", "reason": "HM" | "HF" | "AUT" | "APT" | "HM+AUT" ..., "missing": [...]}

with no value, numerator or denominator key, so it can never be read as zero. The adapter adds two computed reasons
(v1.2.1-f2) for KPIs whose inputs exist but whose value is undefined on the data: DEN0 (zero denominator) and INSUF
(no observation for a median / mean / percentile). Capability reasons are decided first.
"""
from __future__ import annotations

from pathlib import Path

import yaml

try:
    from canonical.contract import ROOT
except ImportError:  # pragma: no cover
    from src.canonical.contract import ROOT

REQUIREMENTS_PATH = ROOT / "profiles" / "admissions" / "kpi_requirements.yaml"
NOT_AVAILABLE_KEYS = {"id", "status", "reason", "missing"}
FORBIDDEN_IN_NOT_AVAILABLE = {"value", "numerator", "denominator", "numerator_value", "denominator_value"}


def load_requirements(path: Path = REQUIREMENTS_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def catalogue(req: dict | None = None) -> list[str]:
    req = req or load_requirements()
    return req["catalogue"]["metrics"] + req["catalogue"]["history"]


def status(kpi_id: str, caps: dict, req: dict | None = None) -> dict:
    req = req or load_requirements()
    if kpi_id not in req["requirements"]:
        raise KeyError(f"no requirements declared for {kpi_id!r}")
    missing = [r for r in req["requirements"][kpi_id] if not caps[r]]
    if not missing:
        return {"id": kpi_id, "status": "available"}
    return {"id": kpi_id, "status": "not_available",
            "reason": "+".join(req["reason_codes"][r] for r in missing), "missing": missing}


def matrix(caps: dict, ids: list[str] | None = None, req: dict | None = None) -> list[dict]:
    req = req or load_requirements()
    return [status(i, caps, req) for i in (ids or catalogue(req))]


def not_available_entry(st: dict) -> dict:
    """The only allowed shape of a not-available result."""
    out = {k: st[k] for k in ("id", "status", "reason", "missing")}
    assert set(out) == NOT_AVAILABLE_KEYS
    return out


def check_no_leak(entries: list[dict]) -> None:
    """Raise if any not_available entry carries a numeric field (value, numerator, denominator)."""
    for e in entries:
        if e["status"] == "not_available" and (set(e) & FORBIDDEN_IN_NOT_AVAILABLE or set(e) != NOT_AVAILABLE_KEYS):
            raise AssertionError(f"not_available entry {e['id']} carries {sorted(set(e) - NOT_AVAILABLE_KEYS)}")
