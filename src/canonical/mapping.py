"""Mapping of the admissions CSV files to canonical tables (profile admissions, mapping admissions-csv/1).

Mapeo de los CSV de admisiones a tablas canónicas.

Every canonical value comes from one source column, a constant of profiles/admissions/mapping_csv_v1.yaml or a
documented one-to-one rule (record_origin from the two flags; discount_amount = campaign + one-time discount).
Nothing is inferred: stage events are created only from the CSV's first-entry columns (entered_*_at, enrolled_at,
closed_lost_at), as first_entry_milestone events, never from current_stage, appointments or activities.
Errors raise CanonicalError with stable M_* codes (see tests/fixtures/mapping_errors).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

try:
    from canonical.contract import Canonical, CanonicalError, Issue, ROOT, normalize_timestamps
except ImportError:  # pragma: no cover
    from src.canonical.contract import Canonical, CanonicalError, Issue, ROOT, normalize_timestamps

MAPPING_PATH = ROOT / "profiles" / "admissions" / "mapping_csv_v1.yaml"
LEAD_TS = ["created_at", "reassigned_at", "first_human_attempt_at", "first_connected_at", "entered_opportunity_at",
           "entered_interview_booked_at", "entered_interview_held_at", "entered_form_completed_at",
           "entered_enrollment_link_sent_at", "enrolled_at", "closed_lost_at", "iloc_started_at", "iloc_ended_at",
           "nurture_started_at", "nurture_ended_at", "next_task_due_at", "snapshot_date"]
ACT_TS = ["activity_at", "interview_scheduled_for", "task_due_at", "task_completed_at"]


def load_mapping(path: Path = MAPPING_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def read_source(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the CSV files as raw strings (empty cell = null), exactly as written."""
    data_dir = Path(data_dir)
    read = lambda n: pd.read_csv(data_dir / n, dtype=str, keep_default_na=False, na_filter=False)
    return read("leads.csv"), read("activities.csv")


def _bool(col: pd.Series, where: str, nullable: bool = False) -> pd.Series:
    allowed = {"True", "False"} | ({""} if nullable else set())
    bad = col[~col.isin(allowed)]
    if len(bad):
        raise CanonicalError(Issue("M_BOOL", where, f"not True/False: {bad.iloc[0]!r}"))
    return col


def _float_sum(a: pd.Series, b: pd.Series, where: str) -> pd.Series:
    out = []
    for x, y in zip(a, b):
        if x == "" or y == "":
            out.append("")
            continue
        try:
            out.append(repr(float(x) + float(y)))
        except ValueError:
            raise CanonicalError(Issue("M_NUMBER", where, f"not a number: {x!r} / {y!r}")) from None
    return pd.Series(out, index=a.index, dtype=object)


def map_admissions_csv(leads: pd.DataFrame, acts: pd.DataFrame, mapping: dict | None = None,
                       dataset_overrides: dict | None = None) -> Canonical:
    """Build canonical tables (strings) from the two admissions CSV frames read with `read_source`."""
    m = mapping or load_mapping()
    dsm = {**m["dataset"], **(dataset_overrides or {})}
    for name, df in (("leads", leads), ("activities", acts)):
        missing = [c for c in m["required_columns"][name] if c not in df.columns]
        if missing:
            raise CanonicalError(Issue("M_MISSING_COLUMN", f"{name}.csv", ", ".join(missing)))
    if dsm["timestamp_mode"] == "naive_wall_clock" and dsm["data_origin"] not in ("synthetic", "legacy"):
        raise CanonicalError(Issue("M_NAIVE_NOT_ALLOWED", "dataset",
                                   f"naive_wall_clock is reserved for synthetic or legacy data, not {dsm['data_origin']!r}"))
    if leads.lead_id.duplicated().any():
        raise CanonicalError(Issue("M_DUPLICATE_ID", "leads.csv", f"lead_id {leads.lead_id[leads.lead_id.duplicated()].iloc[0]!r}"))
    if acts.activity_id.duplicated().any():
        raise CanonicalError(Issue("M_DUPLICATE_ID", "activities.csv", f"activity_id {acts.activity_id[acts.activity_id.duplicated()].iloc[0]!r}"))

    tz, mode = dsm.get("source_timezone"), dsm["timestamp_mode"]
    L, A = leads.copy(), acts.copy()
    for c in LEAD_TS:
        L[c] = normalize_timestamps(L[c], mode, tz, f"leads.{c}")
    for c in ACT_TS:
        A[c] = normalize_timestamps(A[c], mode, tz, f"activities.{c}")
    snaps = L.snapshot_date.unique()
    if len(snaps) != 1 or snaps[0] == "":
        raise CanonicalError(Issue("M_SNAPSHOT", "leads.csv", f"snapshot_date must hold one single value, found {len(snaps)}"))
    dup = _bool(L.is_duplicate, "leads.is_duplicate")
    rea = _bool(L.is_reactivation, "leads.is_reactivation")
    _bool(L.is_synthetic, "leads.is_synthetic")
    _bool(L.reassigned_flag, "leads.reassigned_flag")
    _bool(L.next_step_agreed, "leads.next_step_agreed", nullable=True)
    _bool(A.is_automated, "activities.is_automated")
    if ((dup == "True") & (rea == "True")).any():
        raise CanonicalError(Issue("M_ORIGIN_CONFLICT", "leads.csv", "a row cannot be both duplicate and reactivation"))
    if dsm["data_origin"] == "synthetic" and (L.is_synthetic != "True").any():
        raise CanonicalError(Issue("M_DATA_ORIGIN", "leads.csv", "data_origin synthetic but is_synthetic is not True on every row"))

    dataset = pd.DataFrame([{
        "dataset_id": dsm["dataset_id"], "schema_version": m["schema_version"], "profile": m["profile"],
        "attribute_prefix": m["attribute_prefix"], "data_origin": dsm["data_origin"],
        "history_mode": dsm["history_mode"], "timestamp_mode": mode, "source_timezone": tz or "",
        "snapshot_at": snaps[0], "currency": dsm.get("currency") or ""}])

    rec = pd.DataFrame({k: L[v] for k, v in m["records"].items()})
    rec.insert(2, "record_origin", ["duplicate" if d == "True" else "reactivation" if r == "True" else "original"
                                    for d, r in zip(dup, rea)])
    rec["discount_amount"] = _float_sum(L.campaign_discount, L.one_time_discount, "leads.campaign/one_time_discount")
    order = ["record_id", "person_key", "record_origin", "parent_record_id", "created_at", "entry_route", "source",
             "channel", "product_alias", "owner_first_id", "owner_current_id", "reassigned_at", "current_stage",
             "current_status", "lost_reason", "won_at", "lost_at", "list_amount", "discount_amount", "net_amount"]
    rec = rec[order]

    ev = []
    for col, stage in m["milestones"].items():
        s = L[L[col] != ""]
        ev.append(pd.DataFrame({"event_id": s.lead_id + ":" + stage, "record_id": s.lead_id,
                                "event_kind": "first_entry_milestone", "from_stage": "", "to_stage": stage,
                                "occurred_at": s[col]}))
    events = pd.concat(ev, ignore_index=True) if dsm["history_mode"] != "snapshot_only" else None
    if events is not None:
        events = events.sort_values(["occurred_at", "event_id"], kind="stable").reset_index(drop=True)

    prefix = m["attribute_prefix"] + "_"
    at = []
    for col, vt in m["attributes"].items():
        s = L[L[col] != ""]
        at.append(pd.DataFrame({"record_id": s.lead_id, "attribute": prefix + col, "value_type": vt, "value": s[col]}))
    attrs = pd.concat(at, ignore_index=True).sort_values(["record_id", "attribute"], kind="stable").reset_index(drop=True)

    am = m["appointments"]
    I = A[A.activity_type == "interview"]
    for k, v in am["constants"].items():
        bad = I[I[k] != v]
        if len(bad):
            raise CanonicalError(Issue("M_CONSTANT", "activities.csv", f"interview row {bad.activity_id.iloc[0]} has {k}={bad[k].iloc[0]!r}, expected {v!r}"))
    appts = pd.DataFrame({k: I[v] for k, v in am.items() if k not in ("extensions", "constants")})
    for k, v in am["extensions"].items():
        appts[k] = I[v]
    acm = m["activities"]
    O = A[A.activity_type != "interview"]
    activities = pd.DataFrame({k: O[v] for k, v in acm.items() if k != "extensions"})
    for k, v in acm["extensions"].items():
        activities[k] = O[v]

    tables = {"dataset": dataset, "records": rec.reset_index(drop=True), "activities": activities.reset_index(drop=True),
              "appointments": appts.reset_index(drop=True), "record_attributes": attrs}
    if events is not None:
        tables["stage_events"] = events
    # canonical tables are strings, as stored on disk (empty string = null)
    return Canonical({k: v.astype("str") for k, v in tables.items()})


def map_directory(data_dir: Path, mapping: dict | None = None, dataset_overrides: dict | None = None) -> Canonical:
    leads, acts = read_source(data_dir)
    return map_admissions_csv(leads, acts, mapping, dataset_overrides)
