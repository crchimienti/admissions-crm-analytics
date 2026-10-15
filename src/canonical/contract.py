"""Contract loading, canonical file I/O, typed parsing and strict timestamp handling.

Carga del contrato, lectura y escritura de tablas canónicas, tipado y tratamiento estricto de timestamps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "schema" / "canonical_v0.1.1.yaml"
SCHEMA_VERSION = "crm-canonical/0.1.1"
TABLES = ["dataset", "records", "stage_events", "activities", "appointments", "record_attributes"]
NAIVE_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
OFFSET_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$")


@dataclass
class Issue:
    code: str
    table: str
    detail: str

    def __str__(self):
        return f"{self.code} [{self.table}] {self.detail}"


class CanonicalError(Exception):
    """Raised with one or more issues; `codes` lists their codes (stable, tested)."""

    def __init__(self, issues: list[Issue] | Issue):
        self.issues = issues if isinstance(issues, list) else [issues]
        super().__init__("; ".join(str(i) for i in self.issues[:10]) + (" …" if len(self.issues) > 10 else ""))

    @property
    def codes(self) -> set[str]:
        return {i.code for i in self.issues}


@dataclass
class Canonical:
    """Canonical tables as strings (as stored) plus the typed view built by `typed()`."""
    tables: dict[str, pd.DataFrame]
    typed: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def dataset(self) -> dict:
        return self.tables["dataset"].iloc[0].to_dict()

    def has(self, table: str) -> bool:
        return table in self.tables


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# File I/O (strings only; empty cell = null)
# --------------------------------------------------------------------------- #
def read_canonical(directory: Path) -> Canonical:
    directory = Path(directory)
    tables = {}
    for name in TABLES:
        p = directory / f"{name}.csv"
        if p.exists():
            tables[name] = pd.read_csv(p, dtype=str, keep_default_na=False, na_filter=False)
    return Canonical(tables)


def write_canonical(can: Canonical, directory: Path) -> list[Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for name in TABLES:
        if name in can.tables:
            p = directory / f"{name}.csv"
            can.tables[name].to_csv(p, index=False, lineterminator="\n")
            written.append(p)
    return written


# --------------------------------------------------------------------------- #
# Timestamps
# --------------------------------------------------------------------------- #
def normalize_timestamps(values: pd.Series, mode: str, source_timezone: str | None, where: str) -> pd.Series:
    """Return canonical timestamp strings for one column of source values ('' or NaN = null).

    naive_wall_clock: values must be naive "YYYY-MM-DD HH:MM:SS"; an offset is an error (M_OFFSET_IN_NAIVE).
    utc: values with an offset (or Z) are converted to UTC; naive values are localised with `source_timezone`
         (required, else M_NO_TIMEZONE); ambiguous (DST fall-back) and non-existent (DST spring-forward) local
         times raise M_AMBIGUOUS_TIME / M_NONEXISTENT_TIME. Output "YYYY-MM-DDTHH:MM:SSZ".
    """
    s = values.astype(object).where(values.notna(), "")
    s = s.map(lambda v: str(v).strip())
    out = pd.Series([""] * len(s), index=s.index, dtype=object)
    present = s != ""
    if not present.any():
        return out
    vals = s[present]
    if mode == "naive_wall_clock":
        off = vals[vals.map(lambda v: bool(OFFSET_RE.match(v)))]
        if len(off):
            raise CanonicalError(Issue("M_OFFSET_IN_NAIVE", where, f"value with time-zone offset in naive mode: {off.iloc[0]!r}"))
        bad = vals[~vals.map(lambda v: bool(NAIVE_RE.match(v)))]
        if len(bad):
            raise CanonicalError(Issue("M_UNPARSEABLE_TIMESTAMP", where, f"not 'YYYY-MM-DD HH:MM:SS': {bad.iloc[0]!r}"))
        parsed = pd.to_datetime(vals, format="%Y-%m-%d %H:%M:%S", errors="coerce")
        if parsed.isna().any():
            raise CanonicalError(Issue("M_UNPARSEABLE_TIMESTAMP", where, f"invalid date: {vals[parsed.isna()].iloc[0]!r}"))
        out[present] = parsed.dt.strftime("%Y-%m-%d %H:%M:%S")
        return out
    if mode != "utc":
        raise CanonicalError(Issue("M_TIMESTAMP_MODE", where, f"unknown timestamp mode {mode!r}"))
    has_off = vals.map(lambda v: bool(OFFSET_RE.match(v)))
    naive = vals[~has_off]
    res = pd.Series(index=vals.index, dtype="datetime64[us, UTC]")
    if has_off.any():
        p = pd.to_datetime(vals[has_off], utc=True, errors="coerce", format="ISO8601")
        if p.isna().any():
            raise CanonicalError(Issue("M_UNPARSEABLE_TIMESTAMP", where, f"invalid timestamp: {vals[has_off][p.isna()].iloc[0]!r}"))
        res[has_off] = p
    if len(naive):
        bad = naive[~naive.map(lambda v: bool(NAIVE_RE.match(v)))]
        if len(bad):
            raise CanonicalError(Issue("M_UNPARSEABLE_TIMESTAMP", where, f"not a timestamp: {bad.iloc[0]!r}"))
        if not source_timezone:
            raise CanonicalError(Issue("M_NO_TIMEZONE", where, "naive values in utc mode need dataset.source_timezone"))
        local = pd.to_datetime(naive, format="%Y-%m-%d %H:%M:%S", errors="coerce")
        if local.isna().any():
            raise CanonicalError(Issue("M_UNPARSEABLE_TIMESTAMP", where, f"invalid date: {naive[local.isna()].iloc[0]!r}"))
        try:
            zone = ZoneInfo(source_timezone)
        except Exception:
            raise CanonicalError(Issue("M_TIMEZONE", where, f"unknown time zone {source_timezone!r}")) from None
        conv = []
        for v, t in zip(naive, local):   # value by value so the error names the offending timestamp
            wall = t.to_pydatetime()
            a, b = wall.replace(tzinfo=zone, fold=0), wall.replace(tzinfo=zone, fold=1)
            if a.utcoffset() != b.utcoffset():
                back = a.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)
                code = "M_NONEXISTENT_TIME" if back != wall else "M_AMBIGUOUS_TIME"
                raise CanonicalError(Issue(code, where, f"{v!r} is {'non-existent' if back != wall else 'ambiguous'} in {source_timezone}"))
            conv.append(a.astimezone(timezone.utc))
        res[naive.index] = pd.to_datetime(conv, utc=True)
    out[present] = res.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


def parse_canonical_timestamps(values: pd.Series, mode: str) -> pd.Series:
    """Canonical strings -> datetime64 (naive for naive_wall_clock, UTC-aware for utc). Raises E_TIMESTAMP_FORMAT."""
    s = values.fillna("")
    present = s != ""
    pattern = NAIVE_RE if mode == "naive_wall_clock" else UTC_RE
    bad = s[present & ~s.map(lambda v: bool(pattern.match(v)))]
    if len(bad):
        raise ValueError(bad.iloc[0])
    if mode == "naive_wall_clock":
        return pd.to_datetime(s.where(present, None), format="%Y-%m-%d %H:%M:%S")
    return pd.to_datetime(s.where(present, None), format="%Y-%m-%dT%H:%M:%SZ", utc=True)
