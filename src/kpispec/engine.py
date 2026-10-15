"""Evaluate a kpi-spec/0.1 configuration on a canonical dataset (F3.0).

Evaluación de una configuración kpi-spec/0.1 sobre un dataset canónico.

For each KPI, in this order:
  1. the fields it reads (its own and those of every population it is defined from) are resolved; any field that
     is not available makes the KPI not_available with the joined reasons (FLD, HM, HF, AUT, APT) and the exact list
     of missing fields;
  2. otherwise the operation is computed;
  3. an undefined result is DEN0 (zero denominator) or INSUF (no observation); a true zero stays an available 0.
A not_available result is {id, status, reason, missing} and never carries value, numerator or denominator. One KPI
being not available never prevents the others. This module does not import src/metrics.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from kpispec.fields import FieldResolver
    from kpispec.spec import Spec, filter_fields
except ImportError:  # pragma: no cover
    from src.kpispec.fields import FieldResolver
    from src.kpispec.spec import Spec, filter_fields

NOT_AVAILABLE_KEYS = {"id", "status", "reason", "missing"}


def _kpi_fields(spec: Spec, k: dict) -> list[str]:
    pops = [k[x] for x in ("population", "numerator", "denominator") if x in k]
    out = []
    for p in pops:
        for name in spec.population_chain(p):
            for flt in spec.populations[name].get("where", []):
                out += filter_fields(flt)
    for flt in k.get("numerator_where", []):
        out += filter_fields(flt)
    out += [k[x] for x in ("start", "end", "field") if x in k]
    seen, uniq = set(), []
    for f in out:
        if f not in seen:
            seen.add(f); uniq.append(f)
    return uniq


class Engine:
    def __init__(self, spec: Spec, can):
        self.spec, self.can = spec, can
        self.res = FieldResolver(spec, can)
        self._masks: dict[str, pd.Series] = {}

    def value(self, field):
        return self.res.resolve(field).value

    # filters --------------------------------------------------------------- #
    def _filter(self, flt: dict, idx: pd.Index) -> pd.Series:
        (name, a), = flt.items()
        col = lambda f: self.value(f) if not isinstance(self.value(f), pd.Series) else self.value(f).reindex(idx)
        snap = lambda: self.value("snapshot_at")
        if name == "equals":
            m = col(a[0]) == a[1]
        elif name == "in":
            m = col(a[0]).isin(a[1])
        elif name == "not_null":
            m = col(a).notna()
        elif name == "is_null":
            m = col(a).isna()
        elif name == "age_at_least_days":
            days = self.spec.raw["maturity_days"] if a[1] == "maturity_days" else a[1]
            m = (snap() - col(a[0])) >= pd.Timedelta(days=days)
        elif name == "created_before_snapshot_minus_hours":
            m = col(a[0]) <= snap() - pd.Timedelta(hours=a[1])
        elif name == "at_or_before_snapshot":
            m = col(a) <= snap()
        elif name == "weekday_in":
            m = col(a[0]).dt.weekday.isin(a[1])
        elif name == "duration_le_hours":
            m = (col(a[1]) - col(a[0])) <= pd.Timedelta(hours=a[2])
        else:  # pragma: no cover - the validator rejects unknown filters
            raise ValueError(name)
        return pd.Series(np.asarray(m.fillna(False), dtype=bool), index=idx)

    def mask(self, pop: str) -> pd.Series:
        if pop in self._masks:
            return self._masks[pop]
        p = self.spec.populations[pop]
        idx = self.res.index(self.spec.population_unit(pop))
        m = self.mask(p["from"]).copy() if "from" in p else pd.Series(True, index=idx)
        for flt in p.get("where", []):
            m &= self._filter(flt, idx)
        self._masks[pop] = m
        return m

    # operations ------------------------------------------------------------ #
    def evaluate_kpi(self, kid: str) -> dict:
        k = self.spec.kpis[kid]
        reasons, missing = [], []
        for f in _kpi_fields(self.spec, k):
            r = self.res.resolve(f)
            if not r.ok:
                missing.append(f)
                reasons += [c for c in r.reasons if c not in reasons]
        if missing:
            return {"id": kid, "status": "not_available", "reason": "+".join(reasons), "missing": missing}
        op = k["op"]
        if op == "count":
            n = int(self.mask(k["population"]).sum())
            return self._ok(kid, n, n, None)
        if op == "share":
            P = self.mask(k["population"])
            N = P.copy()
            for flt in k["numerator_where"]:
                N &= self._filter(flt, P.index)
            return self._rate(kid, int(N.sum()), int(P.sum()))
        if op == "ratio":
            N, D = self.mask(k["numerator"]), self.mask(k["denominator"])
            if k["relation"] == "subset_of" and (N & ~D).any():   # impossible by construction: engine fault
                raise AssertionError(f"{kid}: numerator is not a subset of the denominator")
            return self._rate(kid, int(N.sum()), int(D.sum()))
        if op == "duration_stat":
            P = self.mask(k["population"])
            start, end = self.value(k["start"]).reindex(P.index), self.value(k["end"]).reindex(P.index)
            ok = P & start.notna() & end.notna()
            secs = (end[ok] - start[ok]).dt.total_seconds()
            v = secs / 3600 if k["in"] == "hours" else secs.div(86400)
            if len(v) == 0:
                return self._na(kid, "INSUF", ["observations"])
            stat = {"median": v.median, "mean": v.mean, "p90": lambda: v.quantile(0.9)}[k["stat"]]()
            return self._ok(kid, float(stat), None, int(len(v)))
        if op == "field_stat":
            P = self.mask(k["population"])
            v = pd.to_numeric(self.value(k["field"]).reindex(P.index)[P]).dropna()
            if len(v) == 0:
                return self._na(kid, "INSUF", ["observations"])
            return self._ok(kid, float(v.mean()), None, int(len(v)))
        raise ValueError(op)  # pragma: no cover

    @staticmethod
    def _ok(kid, value, num, den):
        return {"id": kid, "status": "available", "value": value, "numerator": num, "denominator": den}

    @staticmethod
    def _na(kid, reason, missing):
        return {"id": kid, "status": "not_available", "reason": reason, "missing": missing}

    def _rate(self, kid, num, den):
        if den == 0:
            return self._na(kid, "DEN0", ["nonzero_denominator"])
        return self._ok(kid, num / den, num, den)


def evaluate(spec: Spec, can) -> list[dict]:
    eng = Engine(spec, can)
    out = [eng.evaluate_kpi(kid) for kid in spec.kpis]
    for e in out:
        if e["status"] == "not_available" and set(e) != NOT_AVAILABLE_KEYS:
            raise AssertionError(f"not_available entry {e['id']} has keys {sorted(e)}")
    return out


def baseline_shape(spec: Spec, result: dict) -> dict:
    """An available result in the F0 metrics document shape (6-decimal rounding, as baseline/metrics_v1.json)."""
    d = spec.kpis[result["id"]]["describe"]
    v = result["value"]
    value = None if v is None or (isinstance(v, float) and np.isnan(v)) else (int(v) if d["kind"] == "count" else round(float(v), 6))
    return {"id": result["id"], **{k: d[k] for k in ("label_en", "label_es", "unit", "kind", "population", "numerator",
                                                      "denominator", "time_basis", "definition_ref")},
            "numerator_value": result["numerator"], "denominator_value": result["denominator"], "value": value}
