"""Map the admissions CSV files to canonical tables (F2).

Mapea los CSV de admisiones a tablas canónicas (F2).

Reads data/leads.csv and data/activities.csv, maps them with profiles/admissions/mapping_csv_v1.yaml, validates the
result against the current contract (schema/canonical_v0.1.1.yaml, which accepts the crm-canonical/0.1 datasets
the mapping emits: the CSV has no event order to carry in seq) and the admissions profile rules, and writes one CSV
per table.
Never writes to data/, baseline/ or reports/f1/. Synthetic data only; no network, no CRM.

Usage: python scripts/map_to_canonical.py [--data data] [--out build/canonical/admissions]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from canonical import mapping  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.contract import write_canonical  # noqa: E402
from canonical.validate import capabilities, validate  # noqa: E402

FROZEN = ("data", "baseline", "reports/f1")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="build/canonical/admissions")
    args = ap.parse_args(argv)
    out = (ROOT / args.out).resolve()
    for f in FROZEN:
        if out == (ROOT / f).resolve() or (ROOT / f).resolve() in out.parents:
            raise SystemExit(f"refusing to write inside {f}/")
    can = validate(mapping.map_directory(ROOT / args.data))
    ad.check_profile(can)
    files = write_canonical(can, out)
    caps = capabilities(can)
    print(f"{can.dataset['schema_version']} · profile admissions · history_mode {caps['history_mode']} · "
          f"is_automated {caps['is_automated']} · appointments {caps['appointments']}")
    for p in files:
        rows = sum(1 for _ in p.open(encoding="utf-8")) - 1
        print(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT).as_posix()}  ({rows} rows)")


if __name__ == "__main__":
    main()
