"""Write the F1 metrics document computed by src/metrics.py.

Escribe el documento de métricas de F1 calculado por src/metrics.py.

Output: reports/f1/metrics_f1.json (same schema as baseline/metrics_v1.json; only `baseline_id` differs).
Never writes to baseline/, which stays frozen as the F0 reference.

Usage: python scripts/export_metrics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402

VERSION_ID = "v1.1.0-f1"
OUT = ROOT / "reports" / "f1" / "metrics_f1.json"


def main():
    # Guard (added in F2): reports/f1/ is frozen since F2; scripts/f2_run.py compares with it without writing there.
    if (ROOT / "src" / "canonical").exists():
        raise SystemExit("export_metrics.py writes reports/f1/, which is frozen since F2 (read-only reference).\n"
                         "Use scripts/f2_run.py, which recomputes the 47 metrics and compares them with reports/f1/metrics_f1.json.")
    ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
    doc = metrics.baseline_document(ctx, VERSION_ID, ROOT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(doc['metrics'])} metrics · {VERSION_ID}")


if __name__ == "__main__":
    main()
