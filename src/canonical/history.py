"""Stage-history indicators computed from canonical stage events (F2).

Indicadores de historial de etapas calculados a partir de los eventos canónicos.

Population: records with record_origin = original (duplicates and reactivations excluded, as in the admissions
eligibility rule). Stage order and terminal stages come from the profile; nothing is inferred from current_stage.

  first_entry        records with at least one entry into each stage          (milestones or full history)
  entry_count        entries into each stage, re-entries included             (full history only)
  regression_events  transitions between open stages that go backwards        (full history only)
  regression_rate    regression transitions / all transition events           (full history only)
  reopen_events      reopen events (terminal -> open stage)                   (full history only)
  reopen_rate        records with >= 1 reopen / records that reached a terminal stage (full history only)
  time_in_stage      median hours between entering a stage and the next stage event, per stage; the last stage
                     of a record is measured until the snapshot (full history only; capability, no fixture value)

Event order (contract rule C09, crm-canonical/0.1.1): within a record, events follow `seq` when the source provides
it; otherwise `occurred_at`. Events of one record that share `occurred_at` without `seq` have an INDETERMINATE order:
it is never resolved by stage, event_id or file position. Only time_in_stage depends on order, so it raises
OrderIndeterminateError in that case. first_entry, entry_count, regressions and reopens do not depend on order:
every transition / reopen event carries its own from_stage and to_stage, and counts and minima are order-free.

Availability is decided by availability.py; these functions refuse to run on an unsuitable history mode, so a
milestone dataset can never produce entry counts, regressions, reopens or durations.
"""
from __future__ import annotations

import pandas as pd


class HistoryModeError(ValueError):
    pass


class OrderIndeterminateError(ValueError):
    """Events of the same record share a timestamp and the source gives no seq: their order is unknown."""

    def __init__(self, records: list[str]):
        self.records = records
        super().__init__(f"event order indeterminate (same occurred_at, no seq) for records {records}")


def ordered_events(events: pd.DataFrame) -> pd.DataFrame:
    """Events sorted by record and source order (seq, else occurred_at). Raise if that order is not determined."""
    if "seq" in events.columns and events["seq"].notna().all():
        return events.sort_values(["record_id", "seq"], kind="stable")
    ties = events[events.duplicated(["record_id", "occurred_at"], keep=False)]
    if len(ties):
        raise OrderIndeterminateError(sorted(ties.record_id.unique()))
    return events.sort_values(["record_id", "occurred_at"], kind="stable")


def _eligible_events(records: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    ids = set(records.record_id[records.record_origin == "original"])
    return events[events.record_id.isin(ids)]


def _stages(rules: dict) -> list[str]:
    s = rules["stages"]
    return [x for x in s["ordered_open"] if x != s["ordered_open"][0]] + s["terminal"]


def first_entry(records, events, history_mode, rules) -> dict:
    if history_mode not in ("full_event_history", "milestone_first_entry"):
        raise HistoryModeError(f"first_entry needs stage milestones, not {history_mode}")
    ev = _eligible_events(records, events)
    kinds = ["first_entry_milestone"] if history_mode == "milestone_first_entry" else ["transition", "reopen"]
    ev = ev[ev.event_kind.isin(kinds)]
    return {st: int(ev[ev.to_stage == st].record_id.nunique()) for st in _stages(rules)}


def _full(records, events, history_mode, what):
    if history_mode != "full_event_history":
        raise HistoryModeError(f"{what} needs full_event_history, not {history_mode}")
    return _eligible_events(records, events)


def entry_count(records, events, history_mode, rules) -> dict:
    ev = _full(records, events, history_mode, "entry_count")
    ev = ev[ev.event_kind.isin(["transition", "reopen"])]
    return {st: int((ev.to_stage == st).sum()) for st in _stages(rules)}


def regressions(records, events, history_mode, rules) -> dict:
    ev = _full(records, events, history_mode, "regression")
    order = {s: i for i, s in enumerate(rules["stages"]["ordered_open"])}
    tr = ev[ev.event_kind == "transition"]
    back = tr[tr.from_stage.isin(order) & tr.to_stage.isin(order)
              & (tr.to_stage.map(order) < tr.from_stage.map(order))]
    n, d = len(back), len(tr)
    return {"events": n, "numerator": n, "denominator": d, "rate": n / d if d else None}


def reopens(records, events, history_mode, rules) -> dict:
    ev = _full(records, events, history_mode, "reopen")
    term = set(rules["stages"]["terminal"])
    reached = set(ev.record_id[ev.event_kind.isin(["transition", "reopen"]) & ev.to_stage.isin(term)])
    ro = ev[ev.event_kind == "reopen"]
    num = len(set(ro.record_id) & reached)
    return {"events": len(ro), "numerator": num, "denominator": len(reached),
            "rate": num / len(reached) if reached else None}


def time_in_stage(records, events, history_mode, rules, snapshot) -> dict:
    ev = _full(records, events, history_mode, "time_in_stage")
    ev = ordered_events(ev[ev.event_kind.isin(["transition", "reopen"])])
    ev = ev.assign(left_at=ev.groupby("record_id").occurred_at.shift(-1))
    term = set(rules["stages"]["terminal"])
    ev = ev[~ev.to_stage.isin(term)]
    hours = (ev.left_at.fillna(snapshot) - ev.occurred_at).dt.total_seconds() / 3600
    med = hours.groupby(ev.to_stage).median()
    return {st: float(med[st]) for st in rules["stages"]["ordered_open"] if st in med.index}
