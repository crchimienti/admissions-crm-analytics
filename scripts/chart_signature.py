"""Structural signature of the notebook charts (v1.4.3-gh): what each chart shows, independent of pixel rendering.

Firma estructural de los gráficos del notebook: lo que muestra cada gráfico, con independencia del renderizado.

The notebook code cells (scripts/build_notebook.py) are executed in this process with matplotlib's Agg backend and the
project's reference rendering settings. At every plt.show() the current figure is described by:
  * figure size in inches; per axes: title, axis labels, axis scales, limits;
  * lines (label, x and y data, colour, style), bars and other rectangles (position, size, colour), text annotations
    (string and position), legend entries, images (shape and a hash of the values), collections (count);
numbers are rounded to 6 decimals. Pixel output, text extents and tick positions (which depend on the layout computed
from font metrics) are deliberately left out: this describes the data, titles and labels of the charts, not their
pixels, so it can be compared exactly on any system, with no tolerance.

Usage:
  python scripts/chart_signature.py --check   # exit 1 if the charts differ from tests/chart_signature_reference.json
  python scripts/chart_signature.py --write   # (re)write the reference; only on the reference environment, when approved
It reads data/ and writes nothing except with --write.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests" / "chart_signature_reference.json"


def _r(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    return round(f, 6)


def _seq(values):
    return [_r(v) for v in list(values)]


def describe_figure(fig) -> dict:
    from matplotlib import colors as mcolors
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    axes = []
    for ax in fig.get_axes():
        a = {"title": [ax.get_title(loc) for loc in ("left", "center", "right")],
             "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(),
             "xscale": ax.get_xscale(), "yscale": ax.get_yscale(),
             "xlim": _seq(ax.get_xlim()), "ylim": _seq(ax.get_ylim()),
             "lines": [], "rectangles": [], "texts": [], "images": [],
             "collections": len(ax.collections)}
        for ln in ax.get_lines():
            if isinstance(ln, Line2D):
                a["lines"].append({"label": ln.get_label(), "x": _seq(ln.get_xdata()), "y": _seq(ln.get_ydata()),
                                   "color": mcolors.to_hex(ln.get_color()), "linestyle": ln.get_linestyle(),
                                   "marker": str(ln.get_marker())})
        for p in ax.patches:
            if isinstance(p, Rectangle):
                a["rectangles"].append({"x": _r(p.get_x()), "y": _r(p.get_y()), "w": _r(p.get_width()),
                                        "h": _r(p.get_height()), "color": mcolors.to_hex(p.get_facecolor())})
        for t in ax.texts:
            a["texts"].append({"text": t.get_text(), "xy": _seq(t.get_position())})
        for im in ax.get_images():
            arr = im.get_array()
            a["images"].append({"shape": list(arr.shape),
                                "values_sha256": hashlib.sha256(json.dumps(_seq(arr.ravel())).encode()).hexdigest()})
        leg = ax.get_legend()
        a["legend"] = [t.get_text() for t in leg.get_texts()] if leg else []
        axes.append(a)
    return {"size_in": _seq(fig.get_size_inches()), "suptitle": fig._suptitle.get_text() if fig._suptitle else "",
            "axes": axes}


def signatures() -> list[dict]:
    """Run the notebook code cells and describe every figure shown."""
    import matplotlib
    matplotlib.use("Agg")
    sys.path.insert(0, str(ROOT / "scripts"))
    import notebook_rendering
    notebook_rendering.configure()
    import matplotlib.pyplot as plt
    import build_notebook

    captured = []

    def show(*_a, **_k):
        captured.append(describe_figure(plt.gcf()))
        plt.close("all")

    plt.show = show
    cwd = os.getcwd()
    os.chdir(ROOT / "notebooks")                      # the notebook runs from notebooks/ (ROOT = Path.cwd().parent)
    try:
        import contextlib
        import io
        ns = {"__name__": "__notebook__", "display": lambda *a, **k: None}
        with contextlib.redirect_stdout(io.StringIO()):   # the cells' printed text is checked by the notebook comparison
            for cell in build_notebook.build().cells:
                if cell.cell_type == "code":
                    exec(compile(cell.source, "<notebook cell>", "exec"), ns)
    finally:
        os.chdir(cwd)
    return captured


def diff(current: list, reference: list) -> list[str]:
    """Exact comparison; returns human-readable differences (empty when identical)."""
    out = []
    if len(current) != len(reference):
        out.append(f"number of charts: {len(current)} vs reference {len(reference)}")
    for i, (c, r) in enumerate(zip(current, reference)):
        if c == r:
            continue
        title = (r["axes"][0]["title"][1] if r["axes"] else "") or f"chart {i + 1}"
        keys = sorted(k for k in set(c) | set(r) if c.get(k) != r.get(k))
        axes_keys = sorted({k for ca, ra in zip(c.get("axes", []), r.get("axes", [])) for k in set(ca) | set(ra)
                            if ca.get(k) != ra.get(k)})
        out.append(f"chart {i + 1} ({title}): differs in {', '.join(keys)}" + (f" [axes: {', '.join(axes_keys)}]" if axes_keys else ""))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    current = signatures()
    if args.write:
        REFERENCE.write_text(json.dumps(current, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"chart signature written: {len(current)} charts -> {REFERENCE.relative_to(ROOT).as_posix()}")
        return 0
    problems = diff(current, json.loads(REFERENCE.read_text(encoding="utf-8")))
    print(f"chart structure: {len(current)} charts — " + ("identical to the reference (data, titles, labels)" if not problems
                                                          else "DIFFERENT: " + "; ".join(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
