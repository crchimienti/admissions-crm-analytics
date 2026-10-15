"""Quick start: print the main synthetic results, computed in memory from data/. Writes no file.

Inicio rápido: imprime los principales resultados sintéticos, calculados en memoria a partir de data/. No escribe
ningún archivo.

Usage / Uso:
  python scripts/show_results.py            # English
  python scripts/show_results.py --lang es  # español
  python scripts/show_results.py --all      # also the 47 reference metrics / también las 47 métricas de referencia

It never runs the generator or the tests, and it does not write Python bytecode caches.
Nunca ejecuta el generador ni las pruebas, y no escribe cachés de bytecode de Python.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True        # read-only: no __pycache__ either

import argparse  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_checks as rc  # noqa: E402

TEXT = {
    "en": {"title": "Admissions CRM analytics — synthetic results",
           "eight": "Eight KPIs of the declarative engine (src/kpispec, profiles/admissions/kpis.yaml)",
           "checks": "Checks", "eq8": "declarative KPIs equal to src/metrics.py",
           "eq47": "reference metrics (src/metrics.py) equal to the frozen F0 baseline",
           "pop": "eligible leads · mature eligible leads (≥ 60 days at the snapshot)",
           "all": "The 47 reference metrics (src/metrics.py)", "na": "not available"},
    "es": {"title": "Analítica CRM de admisiones — resultados sintéticos",
           "eight": "Ocho KPIs del motor declarativo (src/kpispec, profiles/admissions/kpis.yaml)",
           "checks": "Comprobaciones", "eq8": "KPIs declarativos iguales a src/metrics.py",
           "eq47": "métricas de referencia (src/metrics.py) iguales a la línea base congelada F0",
           "pop": "leads elegibles · leads elegibles maduros (≥ 60 días en la fecha de corte)",
           "all": "Las 47 métricas de referencia (src/metrics.py)", "na": "no disponible"},
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", choices=["en", "es"], default="en")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # symbols such as ≥ and − also when output is redirected on Windows
    T, lang = TEXT[args.lang], args.lang
    res = rc.load_results()
    print(T["title"])
    print(rc.SYNTHETIC[lang])
    print("=" * len(T["title"]))
    print(f"{T['pop']}: {rc.fmt_number(res['eligible'], lang)} · {rc.fmt_number(res['mature'], lang)}")
    print()
    print(T["eight"])
    print()
    print(rc.results_table(res, lang))
    ok8 = sum(bool(r.get("equals_metrics_py")) for r in res["eight"])
    print(f"{T['checks']}: {ok8}/8 {T['eq8']} · {res['metrics_equal_f0']}/{res['metrics_total']} {T['eq47']}")
    if args.all:
        print()
        print(T["all"])
        for m in res["live47"]:
            label = m["label_en"] if lang == "en" else m["label_es"]
            value = T["na"] if m["value"] is None else m["value"]
            base = "" if m["denominator_value"] is None else f" [{m['numerator_value']} / {m['denominator_value']}]"
            print(f"- {label}: {value}{base} · {m['population']} · {m['time_basis']}")
    return 0 if ok8 == 8 and res["metrics_equal_f0"] == res["metrics_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
