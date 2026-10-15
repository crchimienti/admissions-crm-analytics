"""Load and validate a kpi-spec/0.1 configuration (F3.0).

Carga y validación de una configuración kpi-spec/0.1.

Every rule comes from schema/kpi_spec_v0.1.yaml. The first violation found raises KpiSpecError with a stable K_*
code; a configuration that does not validate is never evaluated.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schema" / "kpi_spec_v0.1.yaml"
SOURCE_RE = re.compile(r"^(records|dataset|appointments|activities|stage_first_entry|profile)\.([a-z_][a-z0-9_]*)$")
NEEDS_RE = re.compile(r"^activities\.[a-z_][a-z0-9_]*$")


class KpiSpecError(Exception):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")


@dataclass
class Spec:
    raw: dict
    schema: dict

    @property
    def fields(self) -> dict:
        return self.raw["fields"]

    @property
    def populations(self) -> dict:
        return self.raw["populations"]

    @property
    def kpis(self) -> dict:
        return self.raw["kpis"]

    def population_unit(self, name: str) -> str:
        p = self.populations[name]
        return p["unit"] if "unit" in p else self.population_unit(p["from"])

    def population_chain(self, name: str) -> list[str]:
        """The population and all the populations it is defined from, base first."""
        p = self.populations[name]
        return (self.population_chain(p["from"]) if "from" in p else []) + [name]


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_spec(path: Path, schema: dict | None = None) -> Spec:
    return validate_spec(yaml.safe_load(Path(path).read_text(encoding="utf-8")), schema)


def _walk_keys(obj, where="spec"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, where
            yield from _walk_keys(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{where}[{i}]")


def field_unit(name: str, f: dict) -> str:
    kind = SOURCE_RE.match(f["source"]).group(1)
    if kind == "dataset":
        return "dataset"
    if kind == "appointments" or f.get("via"):
        return "appointment"
    if kind == "activities":
        raise KpiSpecError("K_FIELD_SOURCE", f"{name}: activity-level fields are not supported in kpi-spec/0.1")
    return "lead"


def filter_fields(flt: dict) -> list[str]:
    """Declared fields a filter reads (snapshot-relative filters also read snapshot_at)."""
    (name, args), = flt.items()
    if name in ("not_null", "is_null"):
        return [args]
    if name == "at_or_before_snapshot":
        return [args, "snapshot_at"]
    if name in ("age_at_least_days", "created_before_snapshot_minus_hours"):
        return [args[0], "snapshot_at"]
    if name == "duration_le_hours":
        return [args[0], args[1]]
    return [args[0]]


def _check_filter(flt, unit: str, spec: dict, schema: dict, where: str):
    if not isinstance(flt, dict) or len(flt) != 1:
        raise KpiSpecError("K_UNKNOWN_FILTER", f"{where}: a filter is a mapping with exactly one key")
    (name, args), = flt.items()
    if name not in schema["filters"]:
        raise KpiSpecError("K_UNKNOWN_FILTER", f"{where}: {name!r}")
    num = (int, float)
    ok = {
        "equals": lambda a: isinstance(a, list) and len(a) == 2 and isinstance(a[0], str) and not isinstance(a[1], (list, dict)),
        "in": lambda a: isinstance(a, list) and len(a) == 2 and isinstance(a[0], str) and isinstance(a[1], list) and a[1],
        "not_null": lambda a: isinstance(a, str),
        "is_null": lambda a: isinstance(a, str),
        "age_at_least_days": lambda a: isinstance(a, list) and len(a) == 2 and isinstance(a[0], str)
                                       and (a[1] == "maturity_days" or (isinstance(a[1], int) and a[1] >= 0)),
        "created_before_snapshot_minus_hours": lambda a: isinstance(a, list) and len(a) == 2 and isinstance(a[0], str)
                                                         and isinstance(a[1], num) and a[1] >= 0,
        "at_or_before_snapshot": lambda a: isinstance(a, str),
        "weekday_in": lambda a: isinstance(a, list) and len(a) == 2 and isinstance(a[0], str) and isinstance(a[1], list)
                                and a[1] and all(isinstance(d, int) and 0 <= d <= 6 for d in a[1]),
        "duration_le_hours": lambda a: isinstance(a, list) and len(a) == 3 and isinstance(a[0], str)
                                       and isinstance(a[1], str) and isinstance(a[2], num) and a[2] >= 0,
    }[name](args)
    if not ok:
        raise KpiSpecError("K_UNKNOWN_FILTER", f"{where}: wrong arguments for {name}: {args!r}")
    for fld in filter_fields(flt):
        if fld not in spec["fields"]:
            raise KpiSpecError("K_UNKNOWN_FIELD", f"{where}: {fld!r}")
        fu = field_unit(fld, spec["fields"][fld])
        if fu not in (unit, "dataset"):
            raise KpiSpecError("K_UNIT", f"{where}: field {fld!r} has unit {fu}, population unit is {unit}")


def validate_spec(spec: dict, schema: dict | None = None) -> Spec:
    schema = schema or load_schema()
    if not isinstance(spec, dict):
        raise KpiSpecError("K_SPEC_VERSION", "the configuration must be a mapping")
    for k, where in _walk_keys(spec):
        if isinstance(k, str) and k.lower() in schema["forbidden_keys"]:
            raise KpiSpecError("K_FORBIDDEN_KEY", f"{where}: {k!r}")
    req = schema["top_level_keys"]["required"]
    for k in spec:
        if k not in req:
            raise KpiSpecError("K_UNKNOWN_KEY", f"top level: {k!r}")
    for k in req:
        if k not in spec:
            raise KpiSpecError("K_MISSING_KEY", f"top level: {k!r}")
    if spec["spec_version"] != schema["spec_version"]:
        raise KpiSpecError("K_SPEC_VERSION", f"{spec['spec_version']!r} != {schema['spec_version']!r}")
    if spec["time_model"] not in schema["time_models"]:
        raise KpiSpecError("K_TIME_MODEL", f"{spec['time_model']!r} (supported: {schema['time_models']})")
    if not isinstance(spec["maturity_days"], int) or spec["maturity_days"] < 0:
        raise KpiSpecError("K_MISSING_KEY", "maturity_days must be a non-negative integer")

    fs = schema["fields"]
    for name, f in spec["fields"].items():
        if not isinstance(f, dict):
            raise KpiSpecError("K_MISSING_KEY", f"field {name}: must be a mapping")
        for k in f:
            if k not in fs["keys"]:
                raise KpiSpecError("K_UNKNOWN_KEY", f"field {name}: {k!r}")
        for k in fs["required"]:
            if k not in f:
                raise KpiSpecError("K_MISSING_KEY", f"field {name}: {k!r}")
        if not SOURCE_RE.match(str(f["source"])):
            raise KpiSpecError("K_FIELD_SOURCE", f"field {name}: {f['source']!r}")
        kind = SOURCE_RE.match(f["source"]).group(1)
        if f["unit"] not in fs["units"]:
            raise KpiSpecError("K_UNIT", f"field {name}: unknown unit {f['unit']!r}")
        if "via" in f and (f["via"] != "appointments.record_id" or kind != "records"):
            raise KpiSpecError("K_FIELD_SOURCE", f"field {name}: via supports records.<col> via appointments.record_id only")
        if kind == "profile":
            if "needs" not in f or not isinstance(f["needs"], dict) or not f["needs"]:
                raise KpiSpecError("K_MISSING_KEY", f"field {name}: a profile field declares its needs")
            for col, code in f["needs"].items():
                if not NEEDS_RE.match(col) or code not in fs["if_missing_codes"]:
                    raise KpiSpecError("K_FIELD_SOURCE", f"field {name}: need {col!r}: {code!r}")
        elif "if_missing" not in f or f["if_missing"] not in fs["if_missing_codes"]:
            raise KpiSpecError("K_MISSING_KEY", f"field {name}: if_missing must be one of {fs['if_missing_codes']}")
        if field_unit(name, f) != f["unit"]:
            raise KpiSpecError("K_UNIT", f"field {name}: declared unit {f['unit']} but source gives {field_unit(name, f)}")
        if "values" in f and (not isinstance(f["values"], list) or not f["values"]):
            raise KpiSpecError("K_UNKNOWN_KEY", f"field {name}: values must be a non-empty list")
        if "nullable" in f and not isinstance(f["nullable"], bool):
            raise KpiSpecError("K_UNKNOWN_KEY", f"field {name}: nullable must be true or false")

    pops = spec["populations"]
    for name, p in pops.items():
        for k in p:
            if k not in schema["populations"]["keys"]:
                raise KpiSpecError("K_UNKNOWN_KEY", f"population {name}: {k!r}")
        if ("unit" in p) == ("from" in p):
            raise KpiSpecError("K_MISSING_KEY", f"population {name}: exactly one of unit / from")
        if "unit" in p and p["unit"] not in ("lead", "appointment"):
            raise KpiSpecError("K_UNIT", f"population {name}: unit {p['unit']!r}")
        if "from" in p and p["from"] not in pops:
            raise KpiSpecError("K_UNKNOWN_POPULATION", f"population {name}: from {p['from']!r}")
    s = Spec(spec, schema)
    for name in pops:                                   # cycles
        seen, cur = set(), name
        while "from" in pops[cur]:
            if cur in seen:
                raise KpiSpecError("K_UNKNOWN_POPULATION", f"cycle through {name}")
            seen.add(cur); cur = pops[cur]["from"]
    for name, p in pops.items():
        if not isinstance(p.get("where", []), list):
            raise KpiSpecError("K_UNKNOWN_FILTER", f"population {name}: where must be a list")
        for i, flt in enumerate(p.get("where", [])):
            _check_filter(flt, s.population_unit(name), spec, schema, f"population {name}.where[{i}]")

    ops = schema["operations"]
    for kid, k in spec["kpis"].items():
        op = k.get("op")
        if op not in ops:
            raise KpiSpecError("K_UNKNOWN_OP", f"kpi {kid}: {op!r}")
        for key in k:
            if key not in ops[op]["keys"]:
                raise KpiSpecError("K_UNKNOWN_KEY", f"kpi {kid}: {key!r} is not allowed for {op}")
        if op == "ratio" and "relation" not in k:
            raise KpiSpecError("K_RATIO_RELATION_MISSING", f"kpi {kid}")
        needed = {"count": ["population"], "share": ["population", "numerator_where"],
                  "ratio": ["numerator", "denominator"], "duration_stat": ["stat", "population", "start", "end", "in"],
                  "field_stat": ["stat", "population", "field"]}[op] + ["describe"]
        for key in needed:
            if key not in k:
                raise KpiSpecError("K_MISSING_KEY", f"kpi {kid}: {key!r}")
        d = k["describe"]
        for key in schema["describe_keys"]:
            if key not in d:
                raise KpiSpecError("K_MISSING_KEY", f"kpi {kid}.describe: {key!r}")
        for key in d:
            if key not in schema["describe_keys"]:
                raise KpiSpecError("K_UNKNOWN_KEY", f"kpi {kid}.describe: {key!r}")
        for key in ("population", "numerator", "denominator"):
            if key in k and (not isinstance(k[key], str) or k[key] not in pops):
                raise KpiSpecError("K_UNKNOWN_POPULATION", f"kpi {kid}.{key}: {k[key]!r}")
        if op == "share":
            unit = s.population_unit(k["population"])
            if not isinstance(k["numerator_where"], list) or not k["numerator_where"]:
                raise KpiSpecError("K_UNKNOWN_FILTER", f"kpi {kid}: numerator_where must be a non-empty list")
            for i, flt in enumerate(k["numerator_where"]):
                _check_filter(flt, unit, spec, schema, f"kpi {kid}.numerator_where[{i}]")
        if op == "ratio":
            num, den = k["numerator"], k["denominator"]
            if s.population_unit(num) != s.population_unit(den):
                raise KpiSpecError("K_RATIO_UNIT", f"kpi {kid}: {num} is {s.population_unit(num)}, {den} is {s.population_unit(den)}")
            rel = k["relation"]
            if rel not in schema["ratio"]["relations"]:
                raise KpiSpecError("K_RATIO_RELATION", f"kpi {kid}: unknown relation {rel!r}")
            nf, df = pops[num].get("from"), pops[den].get("from")
            if rel == "subset_of" and nf != den:
                raise KpiSpecError("K_RATIO_RELATION", f"kpi {kid}: subset_of needs {num}.from == {den} (found {nf!r})")
            if rel == "same_base" and (nf is None or nf != df):
                raise KpiSpecError("K_RATIO_RELATION", f"kpi {kid}: same_base needs {num}.from == {den}.from ({nf!r} vs {df!r})")
            if rel == "independent_allowed" and not str(k.get("justification", "")).strip():
                raise KpiSpecError("K_RATIO_JUSTIFICATION", f"kpi {kid}")
            if rel != "independent_allowed" and "justification" in k:
                raise KpiSpecError("K_UNKNOWN_KEY", f"kpi {kid}: justification only for independent_allowed")
        if op == "duration_stat":
            unit = s.population_unit(k["population"])
            if k["stat"] not in schema["duration_stats"] or k["in"] not in schema["duration_units"]:
                raise KpiSpecError("K_UNKNOWN_KEY", f"kpi {kid}: stat {k['stat']!r} / in {k['in']!r}")
            if k["stat"] == "p90" and k.get("interpolation") not in schema["interpolations"]:
                raise KpiSpecError("K_MISSING_KEY", f"kpi {kid}: p90 needs interpolation in {schema['interpolations']}")
            for key in ("start", "end"):
                if k[key] not in spec["fields"]:
                    raise KpiSpecError("K_UNKNOWN_FIELD", f"kpi {kid}.{key}: {k[key]!r}")
                if field_unit(k[key], spec["fields"][k[key]]) != unit:
                    raise KpiSpecError("K_UNIT", f"kpi {kid}.{key}: unit differs from the population")
        if op == "field_stat":
            if k["stat"] != "mean" or k["field"] not in spec["fields"]:
                raise KpiSpecError("K_UNKNOWN_FIELD", f"kpi {kid}: field_stat supports mean of a declared field")
        pu = s.population_unit(k.get("population") or k["numerator"])
        if d["unit"] not in ({pu} | ({"deal"} if pu == "lead" else set())):
            raise KpiSpecError("K_UNIT", f"kpi {kid}: describe.unit {d['unit']!r} vs population unit {pu}")
    return s
