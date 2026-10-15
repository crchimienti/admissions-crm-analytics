"""Validation of a canonical dataset against crm-canonical/0.1.1 (own validator, no extra dependency).

Validación de un dataset canónico contra crm-canonical/0.1.1 (validador propio, sin dependencias nuevas).

Checks: schema_version, tables and columns (required, unknown, prefixed extensions), nullability, types, enums,
patterns, primary keys, foreign keys and the neutral rules C01–C08 of the contract (C08 since crm-canonical/0.1.1).
Profile rules (stages, routes,
reactivation parents, amounts) are checked separately by the profile (adapters/<profile>.py).
On success the typed tables are stored in `can.typed`; on failure a CanonicalError lists every issue found.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

try:
    from canonical.contract import Canonical, CanonicalError, Issue, load_contract, parse_canonical_timestamps, SCHEMA_VERSION
except ImportError:  # pragma: no cover
    from src.canonical.contract import Canonical, CanonicalError, Issue, load_contract, parse_canonical_timestamps, SCHEMA_VERSION

INT_RE = re.compile(r"^-?\d+$")


def _cast(col: pd.Series, spec: dict, ts_mode: str, table: str, name: str, issues: list) -> pd.Series:
    t = spec["type"]
    present = col != ""
    vals = col[present]
    where = f"{table}.{name}"
    if t == "bool":
        bad = vals[~vals.isin(["True", "False"])]
        if len(bad):
            issues.append(Issue("E_TYPE", table, f"{name}: not a bool: {bad.iloc[0]!r}"))
            return col
        if present.all():
            return col.eq("True")
        return col.map({"True": True, "False": False, "": np.nan}).astype(object)
    if t == "int":
        bad = vals[~vals.map(lambda v: bool(INT_RE.match(v)))]
        if len(bad):
            issues.append(Issue("E_TYPE", table, f"{name}: not an int: {bad.iloc[0]!r}"))
            return col
        return pd.to_numeric(col.where(present, None)).astype("Int64")
    if t == "float":
        num = pd.to_numeric(vals, errors="coerce")
        if num.isna().any():
            issues.append(Issue("E_TYPE", table, f"{name}: not a number: {vals[num.isna()].iloc[0]!r}"))
            return col
        return pd.to_numeric(col.where(present, None)).astype(float)
    if t == "timestamp":
        try:
            return parse_canonical_timestamps(col, ts_mode)
        except ValueError as e:
            issues.append(Issue("E_TIMESTAMP_FORMAT", table, f"{name}: {e} does not follow timestamp_mode {ts_mode}"))
            return col
    if t == "enum":
        bad = vals[~vals.isin(spec["values"])]
        if len(bad):
            issues.append(Issue("E_ENUM", table, f"{name}: {bad.iloc[0]!r} not in {spec['values']}"))
    if "pattern" in spec:
        bad = vals[~vals.map(lambda v: bool(re.match(spec["pattern"], v)))]
        if len(bad):
            issues.append(Issue("E_PATTERN", table, f"{name}: {bad.iloc[0]!r} does not match {spec['pattern']}"))
    return col.where(present, None).astype("str")


def _attribute_values(attrs: pd.DataFrame, ts_mode: str, issues: list) -> None:
    for vt, g in attrs.groupby("value_type"):
        v = g["value"]
        if vt == "bool":
            bad = v[~v.isin(["True", "False"])]
        elif vt == "int":
            bad = v[~v.map(lambda x: bool(INT_RE.match(x)))]
        elif vt == "float":
            bad = v[pd.to_numeric(v, errors="coerce").isna()]
        elif vt == "timestamp":
            try:
                parse_canonical_timestamps(v, ts_mode); bad = v.iloc[:0]
            except ValueError:
                bad = v
        else:
            bad = v.iloc[:0]
        if len(bad):
            issues.append(Issue("E_TYPE", "record_attributes", f"value {bad.iloc[0]!r} is not a {vt}"))


def validate(can: Canonical, contract: dict | None = None) -> Canonical:
    contract = contract or load_contract()
    issues: list[Issue] = []
    T = can.tables
    if "dataset" not in T or len(T["dataset"]) != 1:
        raise CanonicalError(Issue("E_DATASET", "dataset", "dataset.csv must exist and have exactly one row"))
    ds = T["dataset"].iloc[0]
    accepted = contract.get("accepts_schema_versions", [contract["schema_version"]])
    if ds.get("schema_version") not in accepted or contract["schema_version"] != SCHEMA_VERSION:
        raise CanonicalError(Issue("E_SCHEMA_VERSION", "dataset", f"schema_version {ds.get('schema_version')!r} not in {accepted}"))
    ds_version_rank = accepted.index(ds.get("schema_version"))
    ts_mode = ds.get("timestamp_mode", "")
    hmode = ds.get("history_mode", "")
    prefix = ds.get("attribute_prefix", "") + "_"
    if ts_mode in contract["timestamp_modes"] and ds.get("data_origin") not in contract["timestamp_modes"][ts_mode]["allowed_data_origins"]:
        issues.append(Issue("E_NAIVE_NOT_ALLOWED", "dataset", f"timestamp_mode {ts_mode} not allowed for data_origin {ds.get('data_origin')!r} (C04)"))

    typed: dict[str, pd.DataFrame] = {}
    for tname, tspec in contract["tables"].items():
        if tname not in T:
            if tspec.get("required"):
                issues.append(Issue("E_MISSING_TABLE", tname, "required table missing"))
            continue
        df = T[tname]
        cols = tspec["columns"]
        for c, spec in cols.items():
            if spec.get("required") and c not in df.columns:
                issues.append(Issue("E_MISSING_COLUMN", tname, c))
        for c in df.columns:
            if c not in cols and not (tspec.get("allow_extension_columns") and c.startswith(prefix)):
                issues.append(Issue("E_UNKNOWN_COLUMN", tname, f"{c} (extensions must start with {prefix!r})"))
        if "max_rows" in tspec and len(df) > tspec["max_rows"]:
            issues.append(Issue("E_MAX_ROWS", tname, f"{len(df)} rows > {tspec['max_rows']}"))
        out = {}
        for c in df.columns:
            spec = cols.get(c, {"type": "string", "nullable": True})
            if "since" in spec and ds_version_rank < accepted.index(spec["since"]):
                issues.append(Issue("E_SCHEMA_VERSION", tname, f"{c} requires schema_version {spec['since']} "
                                                                f"(dataset declares {ds.get('schema_version')})"))
            col = df[c].astype(str)
            if not spec.get("nullable", True) and (col == "").any():
                issues.append(Issue("E_NULL", tname, f"{c}: {(col == '').sum()} null value(s) in a non-nullable column"))
            if spec.get("prefixed"):
                bad = col[~col.str.startswith(prefix)]
                if len(bad):
                    issues.append(Issue("E_ATTRIBUTE_PREFIX", tname, f"attribute {bad.iloc[0]!r} must start with {prefix!r}"))
            out[c] = _cast(col, spec, ts_mode, tname, c, issues)
        pk = tspec["primary_key"]
        if all(k in df.columns for k in pk) and df.duplicated(pk).any():
            issues.append(Issue("E_PK_DUPLICATE", tname, f"duplicate {pk}: {df[df.duplicated(pk)][pk].iloc[0].tolist()}"))
        typed[tname] = pd.DataFrame(out, index=df.index)
        if tname == "record_attributes" and {"value_type", "value"} <= set(df.columns):
            _attribute_values(df, ts_mode, issues)

    # foreign keys
    for tname, tspec in contract["tables"].items():
        if tname not in T:
            continue
        for c, spec in tspec["columns"].items():
            ref = spec.get("references")
            if not ref or c not in T[tname].columns:
                continue
            rt, rc = ref.split(".")
            keys = set(T[rt][rc]) if rt in T else set()
            vals = T[tname][c]
            bad = vals[(vals != "") & ~vals.isin(keys)]
            if len(bad):
                issues.append(Issue("E_FK", tname, f"{c}={bad.iloc[0]!r} not found in {ref}"))

    # neutral rules
    hm = contract["history_modes"].get(hmode)
    se = T.get("stage_events")
    if hm is not None and se is not None and len(se) and "event_kind" in se.columns:
        bad = se[~se.event_kind.isin(hm["allowed_event_kinds"])]
        if len(bad):
            issues.append(Issue("E_EVENT_KIND", "stage_events", f"event_kind {bad.event_kind.iloc[0]!r} not allowed in {hmode} (C01)"))
        ms = se[se.event_kind == "first_entry_milestone"]
        if ms.duplicated(["record_id", "to_stage"]).any():
            issues.append(Issue("E_MILESTONE_DUP", "stage_events", "more than one first_entry_milestone per record and stage (C02)"))
        need_from = se.event_kind.isin(["transition", "reopen"])
        if ((need_from & (se.from_stage == "")) | (~need_from & (se.from_stage != ""))).any():
            issues.append(Issue("E_FROM_STAGE", "stage_events", "transition/reopen need from_stage; milestones have none (C03)"))
    if not issues and "dataset" in typed:
        snap = typed["dataset"].snapshot_at.iloc[0]
        for tname, c in (("stage_events", "occurred_at"), ("activities", "occurred_at"), ("appointments", "booked_at")):
            if tname in typed and len(typed[tname]) and (typed[tname][c] > snap).any():
                issues.append(Issue("E_AFTER_SNAPSHOT", tname, f"{c} after snapshot_at (C05)"))
        if "appointments" in typed and len(typed["appointments"]):
            ap = T["appointments"]
            resch = ap.outcome == "rescheduled"
            has_rep = ap.replaced_by_appointment_id != ""
            back = ap.set_index("appointment_id").rescheduled_from_appointment_id
            recip = all(back.get(r, "") == a for a, r in zip(ap.appointment_id[has_rep], ap.replaced_by_appointment_id[has_rep]))
            if (resch != has_rep).any() or not recip:
                issues.append(Issue("E_RESCHEDULE_CHAIN", "appointments", "replaced_by set iff outcome = rescheduled, reciprocal with rescheduled_from (C06)"))
        if "stage_events" in typed and "seq" in typed["stage_events"].columns and len(typed["stage_events"]):
            ev = typed["stage_events"]
            if ev.duplicated(["record_id", "seq"]).any():
                issues.append(Issue("E_SEQ", "stage_events", "seq must be unique within a record (C08)"))
            else:
                o = ev.sort_values(["record_id", "seq"])
                back = o.groupby("record_id").occurred_at.diff() < pd.Timedelta(0)
                if back.any():
                    issues.append(Issue("E_SEQ_ORDER", "stage_events",
                                        f"seq contradicts occurred_at for record {o.record_id[back].iloc[0]} (C08)"))
        if "appointments" in T and ("is_automated" in T["activities"].columns) != ("booking_is_automated" in T["appointments"].columns):
            issues.append(Issue("E_CAPABILITY_MISMATCH", "appointments", "is_automated and booking_is_automated must be both present or both absent (C07)"))
    if hmode == "snapshot_only" and se is not None and len(se):
        issues.append(Issue("E_EVENT_KIND", "stage_events", "snapshot_only datasets carry no stage events (C01)"))
    if issues:
        raise CanonicalError(issues)
    can.typed = typed
    return can


def capabilities(can: Canonical) -> dict:
    """What the dataset provides, read from the data only (nothing is inferred)."""
    contract = load_contract()
    hmode = can.dataset["history_mode"]
    acts = can.tables["activities"]
    return {"history_mode": hmode,
            "stage_milestones": "stage_milestones" in contract["history_modes"][hmode]["provides"],
            "stage_transitions": "stage_transitions" in contract["history_modes"][hmode]["provides"],
            "is_automated": "is_automated" in acts.columns,
            "appointments": "appointments" in can.tables}
