"""Field resolution for kpi-spec/0.1 (F3.0): declared fields -> values, or the reason they are not available.

Resolución de campos: cada campo declarado devuelve sus valores o el motivo por el que no está disponible.

No field is assumed to exist. A source table or column that the load does not provide gives the field's declared
`if_missing` code (FLD, HM, HF, AUT, APT); a profile field checks each of its `needs`. A stage field declared with
`if_missing: HF` requires full stage history; with HM it requires stage milestones. Declared domains (`values`,
`nullable: false`) are enforced: a violation raises KpiDataError (K_FIELD_VALUE) instead of letting a record into a
population silently.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

try:
    from canonical.adapters import admissions as admissions_profile
    from canonical.validate import capabilities
except ImportError:  # pragma: no cover
    from src.canonical.adapters import admissions as admissions_profile
    from src.canonical.validate import capabilities

# Profile functions available to `profile.<name>` sources (admissions only in F3.0).
PROFILE_FUNCTIONS = {"first_human_attempt": admissions_profile.first_human_attempt}


class KpiDataError(Exception):
    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")


@dataclass
class Resolved:
    name: str
    ok: bool
    value: object = None                       # Series indexed by unit id, or a scalar for dataset fields
    reasons: list = field(default_factory=list)


class FieldResolver:
    def __init__(self, spec, can):
        self.spec, self.can = spec, can
        self.T = can.typed
        self._cache: dict[str, Resolved] = {}

    # unit indexes ----------------------------------------------------------- #
    def index(self, unit: str) -> pd.Index:
        if unit == "lead":
            return pd.Index(self.T["records"].record_id, name="record_id")
        if "appointments" in self.T:
            return pd.Index(self.T["appointments"].appointment_id, name="appointment_id")
        return pd.Index([], name="appointment_id")

    def _table_col(self, table: str, col: str):
        t = self.T.get(table)
        if t is None:
            return None, "table"
        if col not in t.columns:
            return None, "column"
        return t, None

    def resolve(self, name: str) -> Resolved:
        if name in self._cache:
            return self._cache[name]
        f = self.spec.fields[name]
        kind, col = f["source"].split(".", 1)
        miss = f.get("if_missing")
        r = None
        if kind == "dataset":
            t, why = self._table_col("dataset", col)
            r = Resolved(name, False, reasons=[miss]) if why else Resolved(name, True, t[col].iloc[0])
        elif kind == "records" and "via" not in f:
            t, why = self._table_col("records", col)
            r = Resolved(name, False, reasons=[miss]) if why else \
                Resolved(name, True, pd.Series(t[col].values, index=self.index("lead")))
        elif kind == "records":                             # via appointments.record_id
            ap, why_a = self._table_col("appointments", "record_id")
            rec, why_r = self._table_col("records", col)
            reasons = ([miss if why_a == "table" else "FLD"] if why_a else []) + (["FLD"] if why_r else [])
            if reasons:                                     # both sides are checked: APT and FLD can combine
                r = Resolved(name, False, reasons=list(dict.fromkeys(reasons)))
            else:
                lookup = pd.Series(rec[col].values, index=rec.record_id.values)
                r = Resolved(name, True, pd.Series(ap.record_id.map(lookup).values, index=self.index("appointment")))
        elif kind == "appointments":
            t, why = self._table_col("appointments", col)
            if why:
                r = Resolved(name, False, reasons=[miss if why == "table" else "FLD"])
            else:
                r = Resolved(name, True, pd.Series(t[col].values, index=self.index("appointment")))
        elif kind == "stage_first_entry":
            caps = capabilities(self.can)
            se = self.T.get("stage_events")
            # a field declared `if_missing: HF` needs full history; any other code needs stage milestones only
            needed = "stage_transitions" if miss == "HF" else "stage_milestones"
            if not caps[needed] or se is None:
                r = Resolved(name, False, reasons=[miss])
            else:
                kinds = ["first_entry_milestone"] if caps["history_mode"] == "milestone_first_entry" else ["transition", "reopen"]
                ev = se[se.event_kind.isin(kinds) & (se.to_stage == col)]
                first = ev.groupby("record_id").occurred_at.min()
                r = Resolved(name, True, first.reindex(self.index("lead")))
        elif kind == "profile":
            acts = self.T.get("activities")
            reasons = []
            for need, code in f["needs"].items():
                c = need.split(".", 1)[1]
                if acts is None or c not in acts.columns:
                    reasons.append(code)
            if reasons:
                r = Resolved(name, False, reasons=reasons)
            else:
                r = Resolved(name, True, PROFILE_FUNCTIONS[col](self.can).reindex(self.index("lead")))
        if r.ok:
            self._check_domain(name, f, r.value)
        self._cache[name] = r
        return r

    @staticmethod
    def _check_domain(name, f, value):
        s = value if isinstance(value, pd.Series) else pd.Series([value])
        if f.get("nullable") is False and s.isna().any():
            raise KpiDataError("K_FIELD_VALUE", f"{name}: {int(s.isna().sum())} null value(s) in a non-nullable field")
        if "values" in f:
            bad = s[s.notna() & ~s.isin(f["values"])]
            if len(bad):
                raise KpiDataError("K_FIELD_VALUE", f"{name}: {bad.iloc[0]!r} is outside {f['values']}")
