"""Admissions adapter: canonical dataset -> the Context of src/metrics.py (F2).

Adaptador de admisiones: dataset canónico -> Context de src/metrics.py.

1. `check_profile` applies the admissions profile rules (profiles/admissions/rules.yaml): stages, routes, statuses,
   lost reasons, reactivation parents, won/lost dates and amounts. These rules are not part of the neutral contract.
2. `to_frames` rebuilds the two frames metrics.py reads (same columns and dtypes as checks.load):
   * mapped columns come back one-to-one (records, record_attributes, activities, appointments);
   * derived lead fields are recomputed with the F0 rules (tested against the CSV):
       first_human_attempt_at  first advisor outbound call/WhatsApp with is_automated = False
       first_connected_at      first connected call, inbound activity or held appointment (its scheduled_for)
       has_open_task / next_task_due_at   tasks with status open or overdue / their earliest due date
       reassigned_flag         reassigned_at is set
       entered_<stage>_at      first entry into the stage, from stage events only (milestone or transition/reopen)
       enrolled_at / closed_lost_at       records.won_at / records.lost_at (state at the snapshot)
   * when the dataset lacks a capability, the columns that depend on it are left empty (NaT / NaN) and every KPI
     that needs them is reported not_available by `evaluate`; nothing is filled in or inferred.
3. `evaluate` runs metrics.baseline_metrics on that Context and the history indicators, and masks every KPI whose
   requirements are not met (availability.py), so no number computed from missing inputs can leave the adapter.
   A value that is undefined on the data although its inputs exist is reported as DEN0 (zero denominator) or INSUF
   (no observation), never as zero (v1.2.1-f2).

Scope: admissions profile only; naive_wall_clock datasets only (SLA weekday / same-day definitions use local wall
clock). No portability claim.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import yaml

try:
    from canonical import availability, history
    from canonical.contract import Canonical, CanonicalError, Issue, ROOT, read_canonical
    from canonical.mapping import load_mapping
    from canonical.validate import capabilities, validate
except ImportError:  # pragma: no cover
    from src.canonical import availability, history
    from src.canonical.contract import Canonical, CanonicalError, Issue, ROOT, read_canonical
    from src.canonical.mapping import load_mapping
    from src.canonical.validate import capabilities, validate

PROFILE_DIR = ROOT / "profiles" / "admissions"


def _metrics():
    """src/metrics.py, imported only when the metrics route is used (v1.3.1-f3).

    Importing this adapter must not load src/metrics.py: the F3 KPI engine reuses `first_human_attempt` from here and
    must stay independent of metrics.py, directly and indirectly.
    """
    try:
        import metrics
    except ImportError:  # pragma: no cover
        from src import metrics
    return metrics
LEAD_STR = ["lead_id", "person_key", "reactivated_from_lead_id", "source", "channel_group", "program_alias",
            "candidate_profile", "entry_path", "first_owner_id", "current_owner_id", "pipeline_stage", "lead_status",
            "last_interview_outcome", "lost_reason", "iloc_end_reason", "nurture_end_reason", "candidate_situation",
            "immediate_interest", "program_interest", "decision_maker", "main_objection", "payment_preference",
            "payment_type"]
LEAD_BOOL = ["is_reactivation", "is_duplicate", "is_synthetic", "reassigned_flag", "has_open_task"]
LEAD_FLOAT = ["list_price", "campaign_discount", "one_time_discount", "net_price"]
ACT_STR = ["activity_id", "lead_id", "actor_type", "actor_id", "activity_type", "direction", "sequence_name",
           "sequence_step", "call_outcome", "email_status", "interview_outcome", "interviewer_id",
           "rescheduled_from_activity_id", "replaced_by_activity_id", "rebooked_after_activity_id", "task_status"]
ACT_FLOAT = ["sequence_instance", "business_day_index"]
MILESTONE_COLUMNS = {"opportunity": "entered_opportunity_at", "interview_booked": "entered_interview_booked_at",
                     "interview_held": "entered_interview_held_at", "form_completed": "entered_form_completed_at",
                     "enrollment_link_sent": "entered_enrollment_link_sent_at"}


def load_rules(path: Path = PROFILE_DIR / "rules.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_config(path: Path = ROOT / "config" / "simulation_params.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. Profile rules
# --------------------------------------------------------------------------- #
def _attrs_wide(can: Canonical) -> pd.DataFrame:
    a = can.tables.get("record_attributes")
    if a is None or a.empty:
        return pd.DataFrame(index=pd.Index([], name="record_id"))
    return a.pivot(index="record_id", columns="attribute", values="value")


def check_profile(can: Canonical, rules: dict | None = None) -> None:
    rules = rules or load_rules()
    if can.dataset["profile"] != rules["profile"] or can.dataset["attribute_prefix"] != rules["attribute_prefix"]:
        raise CanonicalError(Issue("P_PROFILE", "dataset", f"profile {can.dataset['profile']!r} is not {rules['profile']!r}"))
    R = can.tables["records"]
    st = rules["stages"]
    stages = set(st["ordered_open"]) | set(st["terminal"])
    issues = []

    def add(code, table, mask, detail):
        if mask.any():
            first = R.record_id[mask].iloc[0] if table == "records" and len(mask) == len(R) else ""
            issues.append(Issue(code, table, f"{detail} ({int(mask.sum())} row(s){', e.g. ' + first if first else ''})"))

    add("P_STAGE", "records", ~R.current_stage.isin(stages), "current_stage outside the profile stages")
    se = can.tables.get("stage_events")
    if se is not None and len(se):
        bad = ~se.to_stage.isin(stages) | ((se.from_stage != "") & ~se.from_stage.isin(stages))
        if bad.any():
            issues.append(Issue("P_STAGE", "stage_events", f"stage outside the profile stages: {se[bad].event_id.iloc[0]}"))
    orig = R.record_origin
    add("P_ROUTE", "records", (orig != "duplicate") & ~R.entry_route.isin(rules["entry_routes"]), "entry_route not in the profile routes")
    add("P_STATUS", "records", (R.current_status != "") & ~R.current_status.isin(rules["statuses"]), "current_status not in the profile statuses")
    add("P_REACTIVATION_PARENT_MISSING", "records", (orig == "reactivation") & (R.parent_record_id == ""),
        "reactivation without parent_record_id")
    add("P_PARENT_NOT_ALLOWED", "records", (orig != "reactivation") & (R.parent_record_id != ""),
        "parent_record_id on a record that is not a reactivation")
    P = R.set_index("record_id")
    bad_parent = []
    for _, r in R[(orig == "reactivation") & (R.parent_record_id != "")].iterrows():
        p = P.loc[r.parent_record_id] if r.parent_record_id in P.index else None
        if (p is None or p.person_key != r.person_key or not p.created_at < r.created_at
                or p.current_stage != st["lost"] or p.lost_reason != "future_intake"):
            bad_parent.append(r.record_id)
    if bad_parent:
        issues.append(Issue("P_REACTIVATION_PARENT_INVALID", "records",
                            f"parent must exist, share person_key, be older and be closed_lost/future_intake: {bad_parent[0]}"))
    add("P_WON_LOST", "records", (R.won_at != "") != (R.current_stage == st["won"]), "won_at set iff current_stage = closed_won")
    add("P_WON_LOST", "records", (R.lost_at != "") != (R.current_stage == st["lost"]), "lost_at set iff current_stage = closed_lost")
    add("P_LOST_REASON", "records", (R.lost_reason != "") & (~R.lost_reason.isin(rules["lost_reasons"]) | (R.current_stage != st["lost"])),
        "lost_reason not in the profile reasons or record not closed_lost")
    amt = R[["list_amount", "discount_amount", "net_amount"]] != ""
    add("P_AMOUNTS", "records", amt.any(axis=1) & ~amt.all(axis=1), "amounts must be all set or all null")
    full = R[amt.all(axis=1)]
    cents = lambda s: (pd.to_numeric(s) * 100).round().astype("int64")
    if len(full):
        bad = cents(full.list_amount) - cents(full.discount_amount) != cents(full.net_amount)
        if bad.any():
            issues.append(Issue("P_AMOUNTS", "records", f"list - discount != net: {full.record_id[bad].iloc[0]}"))
        W = _attrs_wide(can).reindex(full.record_id)
        p = rules["attribute_prefix"] + "_"
        camp, one = W.get(p + "campaign_discount"), W.get(p + "one_time_discount")
        if camp is None or one is None or camp.isna().any() or one.isna().any():
            issues.append(Issue("P_DISCOUNT_SPLIT", "record_attributes", "adm_campaign_discount and adm_one_time_discount are required when amounts are set"))
        else:
            bad = cents(camp.values) + cents(one.values) != cents(full.discount_amount.values)
            if bad.any():
                issues.append(Issue("P_DISCOUNT_SPLIT", "record_attributes", f"campaign + one-time != discount_amount: {full.record_id.values[bad][0]}"))
    if issues:
        raise CanonicalError(issues)


def record_outcome(records: pd.DataFrame, rules: dict | None = None) -> pd.Series:
    """open / won / lost per record, from current_stage and the profile's won / lost stages.

    current_status is NOT used: it holds operational statuses (new, working, iloc_sequence, nurture, closed_won,
    closed_lost). A record in nurture, for example, has current_stage closed_lost, so its outcome is lost.
    """
    rules = rules or load_rules()
    st = rules["stages"]
    stage = records.current_stage
    return pd.Series(np.select([stage == st["won"], stage == st["lost"]], ["won", "lost"], "open"), index=records.index)


def load(directory: Path) -> Canonical:
    """Read, validate against the contract and check the admissions profile rules."""
    can = validate(read_canonical(directory))
    check_profile(can)
    return can


# --------------------------------------------------------------------------- #
# 2. Frames for metrics.py
# --------------------------------------------------------------------------- #
def _attr_column(W: pd.DataFrame, a: pd.DataFrame, name: str, idx: pd.Index):
    if name not in W.columns:
        return pd.Series(np.nan, index=idx, dtype=object)
    return W[name].reindex(idx)


FIRST_HUMAN_ATTEMPT_NEEDS = ("actor_type", "direction", "activity_type", "is_automated")


def first_human_attempt(can: Canonical) -> pd.Series:
    """Profile function (F0 rule): first advisor outbound call or WhatsApp with is_automated = False, per record.

    Indexed by record_id; records without such an activity are absent. Needs activities.actor_type, direction,
    activity_type and is_automated (the caller checks their presence; a missing column raises KeyError).
    Shared by `to_frames` (src/metrics.py route) and the F3 KPI engine (src/kpispec), so both use one rule.
    """
    Ac = can.typed["activities"]
    missing = [c for c in FIRST_HUMAN_ATTEMPT_NEEDS if c not in Ac.columns]
    if missing:
        raise KeyError(f"activities columns missing: {missing}")
    man = Ac[(Ac.actor_type == "advisor") & (Ac.direction == "outbound") & Ac.activity_type.isin(["call", "whatsapp"])
             & ~Ac.is_automated.astype(bool)]
    return man.groupby("record_id").occurred_at.min()


def to_frames(can: Canonical, mapping: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not can.typed:
        raise ValueError("validate the dataset first (canonical.validate.validate)")
    if can.dataset["timestamp_mode"] != "naive_wall_clock":
        raise CanonicalError(Issue("A_TIMESTAMP_MODE", "dataset", "the admissions adapter supports naive_wall_clock only in F2"))
    m = mapping or load_mapping()
    T = can.typed
    caps = capabilities(can)
    R = T["records"].set_index("record_id", drop=False)
    ds = T["dataset"].iloc[0]
    idx = R.index
    prefix = can.dataset["attribute_prefix"] + "_"

    # activities and appointments back to the activity rows of activities.csv
    Ac = T["activities"]
    acts = pd.DataFrame({
        "activity_id": Ac.activity_id, "lead_id": Ac.record_id, "activity_at": Ac.occurred_at,
        "actor_type": Ac.actor_type, "actor_id": Ac.actor_id, "activity_type": Ac.activity_type,
        "direction": Ac.direction,
        "is_automated": Ac.is_automated if caps["is_automated"] else np.nan,
        "sequence_name": Ac.sequence_name, "sequence_step": Ac.sequence_step,
        "sequence_instance": Ac.get(prefix + "sequence_instance"), "business_day_index": Ac.get(prefix + "business_day_index"),
        "call_outcome": Ac.call_outcome, "email_status": Ac.email_status,
        "task_due_at": Ac.task_due_at, "task_completed_at": Ac.task_completed_at, "task_status": Ac.task_status})
    parts = [acts]
    if caps["appointments"]:
        Ap = T["appointments"]
        const = m["appointments"]["constants"]
        parts.append(pd.DataFrame({
            "activity_id": Ap.appointment_id, "lead_id": Ap.record_id, "activity_at": Ap.booked_at,
            "actor_type": Ap.booked_by_actor_type, "actor_id": Ap.booked_by_actor_id, "activity_type": "interview",
            "direction": const["direction"],
            "is_automated": Ap.booking_is_automated if caps["is_automated"] else np.nan,
            "sequence_name": const["sequence_name"], "sequence_step": Ap.get(prefix + "booking_sequence_step"),
            "interview_scheduled_for": Ap.scheduled_for, "interview_outcome": Ap.outcome, "interviewer_id": Ap.host_id,
            "rescheduled_from_activity_id": Ap.rescheduled_from_appointment_id,
            "replaced_by_activity_id": Ap.replaced_by_appointment_id,
            "rebooked_after_activity_id": Ap.rebooked_after_appointment_id}))
    A = pd.concat(parts, ignore_index=True).sort_values("activity_id", kind="stable").reset_index(drop=True)
    A = A.reindex(columns=m["required_columns"]["activities"])
    for c in ACT_STR:
        A[c] = A[c].astype("str")
    for c in ACT_FLOAT:
        A[c] = pd.to_numeric(A[c]).astype(float)
    for c in ("activity_at", "interview_scheduled_for", "task_due_at", "task_completed_at"):
        A[c] = pd.to_datetime(A[c]).astype("datetime64[us]")
    if caps["is_automated"]:
        A["is_automated"] = A.is_automated.astype(bool)
    else:
        A["is_automated"] = np.nan   # unknown: nothing counts as manual; dependent KPIs are masked

    # derived lead fields (F0 rules)
    first_attempt = first_human_attempt(can) if caps["is_automated"] else pd.Series(dtype="datetime64[us]")
    conn = [A.loc[(A.activity_type == "call") & (A.call_outcome == "connected"), ["lead_id", "activity_at"]],
            A.loc[A.direction == "inbound", ["lead_id", "activity_at"]]]
    if caps["appointments"]:
        conn.append(A.loc[(A.activity_type == "interview") & (A.interview_outcome == "held"), ["lead_id", "interview_scheduled_for"]]
                    .rename(columns={"interview_scheduled_for": "activity_at"}))
    first_conn = pd.concat(conn).groupby("lead_id").activity_at.min()
    tasks = A[(A.activity_type == "task") & A.task_status.isin(["open", "overdue"])]
    next_due = tasks.groupby("lead_id").task_due_at.min()

    entered = {c: pd.Series(pd.NaT, index=idx, dtype="datetime64[us]") for c in MILESTONE_COLUMNS.values()}
    if caps["stage_milestones"]:
        se = T["stage_events"]
        kinds = ["first_entry_milestone"] if can.dataset["history_mode"] == "milestone_first_entry" else ["transition", "reopen"]
        se = se[se.event_kind.isin(kinds)]
        for stage, col in MILESTONE_COLUMNS.items():
            entered[col] = se[se.to_stage == stage].groupby("record_id").occurred_at.min().reindex(idx)

    W = _attrs_wide(can)
    att = lambda n: _attr_column(W, None, prefix + n, idx)
    L = pd.DataFrame(index=idx)
    L["lead_id"] = R.record_id
    L["person_key"] = R.person_key
    L["is_reactivation"] = R.record_origin == "reactivation"
    L["reactivated_from_lead_id"] = R.parent_record_id
    L["is_duplicate"] = R.record_origin == "duplicate"
    L["is_synthetic"] = ds.data_origin == "synthetic"
    L["created_at"] = R.created_at
    L["source"], L["channel_group"], L["program_alias"] = R.source, R.channel, R.product_alias
    L["candidate_profile"] = att("candidate_profile")
    L["entry_path"] = R.entry_route
    L["first_owner_id"], L["current_owner_id"] = R.owner_first_id, R.owner_current_id
    L["reassigned_flag"] = R.reassigned_at.notna()
    L["reassigned_at"] = R.reassigned_at
    L["first_human_attempt_at"] = first_attempt.reindex(idx)
    L["first_connected_at"] = first_conn.reindex(idx)
    for col in MILESTONE_COLUMNS.values():
        L[col] = entered[col]
    L["enrolled_at"], L["closed_lost_at"] = R.won_at, R.lost_at
    L["pipeline_stage"], L["lead_status"] = R.current_stage, R.current_status
    L["last_interview_outcome"] = att("last_interview_outcome")
    L["lost_reason"] = R.lost_reason
    for c in ("iloc_started_at", "iloc_ended_at", "iloc_end_reason", "iloc_episode_count", "nurture_started_at",
              "nurture_ended_at", "nurture_end_reason"):
        L[c] = att(c)
    L["has_open_task"] = idx.isin(tasks.lead_id)
    L["next_task_due_at"] = next_due.reindex(idx)
    for c in ("candidate_situation", "immediate_interest", "program_interest", "decision_maker", "main_objection",
              "payment_preference"):
        L[c] = att(c)
    L["next_step_agreed"] = att("next_step_agreed").map({"True": True, "False": False}).astype(object)
    L["next_step_agreed"] = L.next_step_agreed.where(L.next_step_agreed.notna(), np.nan)
    L["payment_type"] = att("payment_type")
    L["list_price"] = R.list_amount
    L["campaign_discount"], L["one_time_discount"] = att("campaign_discount"), att("one_time_discount")
    L["net_price"] = R.net_amount
    L["snapshot_date"] = ds.snapshot_at
    L = L.reset_index(drop=True).reindex(columns=m["required_columns"]["leads"])
    for c in LEAD_STR:
        L[c] = L[c].astype("str")
    for c in LEAD_BOOL:
        L[c] = L[c].astype(bool)
    for c in LEAD_FLOAT:
        L[c] = pd.to_numeric(L[c]).astype(float)
    ts = [c for c in L.columns if c.endswith("_at") or c == "snapshot_date"]
    for c in ts:
        L[c] = pd.to_datetime(L[c]).astype("datetime64[us]")
    ep = pd.to_numeric(L.iloc_episode_count)
    L["iloc_episode_count"] = ep.astype("int64") if ep.notna().all() else ep
    return L, A


def build_context(can: Canonical, cfg: dict | None = None, maturity_days: int = 60) -> "metrics.Context":
    leads, acts = to_frames(can)
    gt = pd.DataFrame({"lead_id": pd.Series(dtype="str"), "issue_type": pd.Series(dtype="str"),
                       "detail": pd.Series(dtype="str")})   # anomaly ground truth is not part of the canonical model
    return _metrics().build_context(leads, acts, gt, cfg or load_config(), maturity_days=maturity_days)


# --------------------------------------------------------------------------- #
# 3. Evaluation with availability masks
# --------------------------------------------------------------------------- #
def history_indicators(can: Canonical, rules: dict | None = None) -> dict:
    """Available history indicators only (callers ask availability first)."""
    rules = rules or load_rules()
    T = can.typed
    caps = capabilities(can)
    hmode = caps["history_mode"]
    R = T["records"]
    E = T.get("stage_events")
    if E is None:
        E = pd.DataFrame(columns=["event_id", "record_id", "event_kind", "from_stage", "to_stage", "occurred_at"])
    out = {}
    if caps["stage_milestones"]:
        out["first_entry"] = {"value": history.first_entry(R, E, hmode, rules)}
    if caps["stage_transitions"]:
        out["entry_count"] = {"value": history.entry_count(R, E, hmode, rules)}
        rg = history.regressions(R, E, hmode, rules)
        out["regression_events"] = {"value": rg["events"]}
        out["regression_rate"] = {"value": rg["rate"], "numerator": rg["numerator"], "denominator": rg["denominator"]}
        ro = history.reopens(R, E, hmode, rules)
        out["reopen_events"] = {"value": ro["events"]}
        out["reopen_rate"] = {"value": ro["rate"], "numerator": ro["numerator"], "denominator": ro["denominator"]}
        try:
            out["time_in_stage"] = {"value": history.time_in_stage(R, E, hmode, rules, T["dataset"].snapshot_at.iloc[0])}
        except history.OrderIndeterminateError as err:   # same timestamp, no seq: order unknown, nothing invented
            out["time_in_stage"] = {"undetermined": "ORD", "records": err.records}
    return out


def _clean(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


# Reasons for a KPI whose inputs exist but whose value is undefined on this data (computed after the capability check):
#   DEN0   the rate's denominator is zero (e.g. no held interview -> forms / held interviews is undefined)
#   INSUF  a median / mean / percentile has no observation to summarise
# Capability reasons (HM, HF, AUT, APT: a module or table is absent) always take precedence.
#   ORD    an order-dependent indicator (time_in_stage) on events whose order is indeterminate: same occurred_at in
#          one record and no seq (contract rule C09, crm-canonical/0.1.1)
COMPUTED_REASONS = {"DEN0": ["nonzero_denominator"], "INSUF": ["observations"], "ORD": ["event_order"]}


def undefined_reason(kind: str, value, denominator) -> str | None:
    """None if the value is defined; DEN0 / INSUF if it is undefined for a known reason; raise otherwise."""
    if value is not None and not (isinstance(value, float) and np.isnan(value)):
        return None
    den = None if denominator is None else int(denominator)
    if kind == "rate" and den == 0:
        return "DEN0"
    if kind in ("median", "mean", "p90") and not den:
        return "INSUF"
    raise ValueError(f"undefined {kind} value with denominator {denominator!r}: no documented reason")


def computed_not_available(kpi_id: str, reason: str) -> dict:
    return {"id": kpi_id, "status": "not_available", "reason": reason, "missing": list(COMPUTED_REASONS[reason])}


def catalogue_availability(can: Canonical) -> list[dict]:
    """Status of the 31 catalogue indicators, from the dataset's capabilities only (no metric is computed)."""
    req = availability.load_requirements()
    return availability.matrix(capabilities(can), req=req)


def evaluate(can: Canonical, cfg: dict | None = None, maturity_days: int = 60) -> dict:
    """All 47 baseline metrics + 7 history indicators, each available (with value) or not_available (no value).

    Order of decisions per KPI: (1) capability requirements (HM, HF, AUT, APT: module absent); (2) if available, the
    value computed by src/metrics.py or history.py; (3) an undefined value is DEN0 (zero denominator) or INSUF (no
    observations), never zero. One KPI being not available never prevents computing the others.
    """
    return evaluate_context(build_context(can, cfg, maturity_days), can)


def evaluate_context(ctx, can: Canonical) -> dict:
    req = availability.load_requirements()
    caps = capabilities(can)
    results = _metrics().baseline_metrics(ctx)
    baseline, hist_entries = [], []
    for r in results:
        st = availability.status(r.id, caps, req)
        if st["status"] != "available":
            baseline.append(availability.not_available_entry(st))
            continue
        why = undefined_reason(r.kind, r.value, r.denominator_value)
        baseline.append(computed_not_available(r.id, why) if why else {"status": "available", **r.to_dict()})
    hist = history_indicators(can)
    for hid in req["catalogue"]["history"]:
        st = availability.status(hid, caps, req)
        if st["status"] != "available":
            hist_entries.append(availability.not_available_entry(st))
            continue
        if "undetermined" in hist[hid]:
            hist_entries.append(computed_not_available(hid, hist[hid]["undetermined"]))
            continue
        h = {k: _clean(v) for k, v in hist[hid].items()}
        why = undefined_reason("rate", h["value"], h["denominator"]) if "denominator" in h else None
        hist_entries.append(computed_not_available(hid, why) if why else {"id": hid, "status": "available", **h})
    by_id = {e["id"]: e for e in baseline}
    cat = []
    for mid in req["catalogue"]["metrics"]:
        e = by_id[mid]
        if e["status"] == "available":
            cat.append({"id": mid, "status": "available", "value": e["value"], "numerator": e["numerator_value"],
                        "denominator": e["denominator_value"]})
        else:
            cat.append(dict(e))
    cat += hist_entries
    availability.check_no_leak(baseline + cat)
    return {"capabilities": caps, "baseline_metrics": baseline, "catalogue": cat}
