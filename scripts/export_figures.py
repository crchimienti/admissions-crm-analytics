"""Export three README figures from the executed notebook (v1.4.0-gh). Nothing is recomputed or redrawn.

Exporta tres gráficos del README desde el notebook ejecutado. No se recalcula ni se vuelve a dibujar nada.

Each figure is the PNG output of the notebook cell that draws it (found by the chart title in the cell source),
base64-decoded byte for byte. The notebook itself is pinned by the F1 manifest, so the PNG files are deterministic.

Usage / Uso:
  python scripts/export_figures.py          # write docs/img/*.png
  python scripts/export_figures.py --check  # exit 1 if docs/img/*.png differ from the notebook outputs
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "admissions_analysis.ipynb"
OUT = ROOT / "docs" / "img"
# output file -> chart title as written in scripts/build_notebook.py (each title marks exactly one code cell)
FIGURES = {
    "funnel_mature_cohorts.png": "Funnel, mature cohorts — leads reaching each milestone (synthetic)",
    "main_kpi_by_cohort.png": "Main KPI by cohort — mature cohorts only (synthetic)",
    "show_rate_by_month.png": "Per-appointment show rate by appointment month (synthetic)",
}


def extract() -> dict[str, bytes]:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    out = {}
    for name, title in FIGURES.items():
        cells = [c for c in nb["cells"] if c["cell_type"] == "code" and title in "".join(c["source"])]
        if len(cells) != 1:
            raise SystemExit(f"{name}: expected one notebook cell titled {title!r}, found {len(cells)}")
        pngs = [o["data"]["image/png"] for o in cells[0].get("outputs", []) if "image/png" in o.get("data", {})]
        if len(pngs) != 1:
            raise SystemExit(f"{name}: expected one PNG output in its cell, found {len(pngs)} (is the notebook executed?)")
        data = pngs[0]
        out[name] = base64.b64decode("".join(data) if isinstance(data, list) else data)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    figures = extract()
    if args.check:
        bad = [n for n, b in figures.items() if not (OUT / n).exists() or (OUT / n).read_bytes() != b]
        print("figures:", "identical to the notebook outputs" if not bad else f"DIFFER: {bad}")
        return 1 if bad else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in figures.items():
        (OUT / name).write_bytes(data)
        print(f"{(OUT / name).relative_to(ROOT).as_posix()} ({len(data):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
