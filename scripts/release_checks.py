"""Shared checks for the GitHub preparation (v1.4.0-gh). Read-only: nothing here writes a file.

Comprobaciones compartidas de la preparación para GitHub (v1.4.0-gh). Solo lectura: aquí nada escribe archivos.

Used by scripts/show_results.py, scripts/release_run.py and tests/test_release.py:
  * repository files: the tree minus the .gitignore rules (a simplified matcher, see `is_ignored`);
  * results: the eight declarative KPIs and the 47 reference metrics, computed from data/ in memory;
  * the README results block, internal links, and a security scan with its stated limits.
"""
from __future__ import annotations

import csv
import fnmatch
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALWAYS_EXCLUDED = {".git"}
RESULTS_START, RESULTS_END = "<!-- results:start -->", "<!-- results:end -->"
SYNTHETIC = {"en": "Synthetic data (seed 42). Not real historical results; no causal claims.",
             "es": "Datos sintéticos (semilla 42). No son resultados históricos reales; sin afirmaciones causales."}


# --------------------------------------------------------------------------- #
# Repository files
# --------------------------------------------------------------------------- #
def ignore_patterns() -> list[str]:
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")]


def is_ignored(rel: str, patterns: list[str] | None = None) -> bool:
    """Simplified .gitignore semantics, enough for this repository's rules: `name/` ignores any directory with that
    name; any other pattern is a glob matched against the file name and against the whole relative path. Negations
    (`!`) are not used in this repository and are not supported here. `git check-ignore` is the authoritative check
    once a repository exists."""
    patterns = ignore_patterns() if patterns is None else patterns
    parts = rel.split("/")
    for pat in patterns:
        if pat.endswith("/"):
            if pat[:-1] in parts[:-1]:
                return True
        elif fnmatch.fnmatch(parts[-1], pat) or fnmatch.fnmatch(rel, pat):
            return True
    return False


def repo_files():
    """(relative posix path, Path) of every file Git would track, sorted."""
    pats = ignore_patterns()
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and not set(rel.split("/")) & ALWAYS_EXCLUDED and not is_ignored(rel, pats):
            yield rel, p


# --------------------------------------------------------------------------- #
# Results (in memory, from data/)
# --------------------------------------------------------------------------- #
def _import_paths():
    for d in (ROOT / "src", ROOT / "scripts"):
        if str(d) not in sys.path:
            sys.path.insert(0, str(d))


def load_results() -> dict:
    """The eight declarative KPIs (src/kpispec) and the 47 reference metrics (src/metrics.py), from data/."""
    _import_paths()
    import metrics
    from canonical import mapping
    from canonical.adapters import admissions as ad
    from canonical.validate import validate
    from kpispec import engine
    from kpispec.spec import load_spec
    spec = load_spec(ROOT / "profiles" / "admissions" / "kpis.yaml")
    ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
    ref47 = json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8"))["metrics"]
    live47 = [m.to_dict() for m in metrics.baseline_metrics(ctx)]
    can = validate(mapping.map_directory(ROOT / "data"))
    ad.check_profile(can)
    eight = []
    live = {m["id"]: m for m in live47}
    for r in engine.evaluate(spec, can):
        if r["status"] == "available":
            shaped = engine.baseline_shape(spec, r)
            eight.append({**shaped, "status": "available", "equals_metrics_py": shaped == live[r["id"]]})
        else:
            eight.append({**r, **{k: spec.kpis[r["id"]]["describe"][k] for k in ("label_en", "label_es", "population", "time_basis")}})
    return {"snapshot": str(ctx.SNAP), "eight": eight, "live47": live47,
            "metrics_equal_f0": sum(a == b for a, b in zip(live47, ref47)), "metrics_total": len(ref47),
            "eligible": len(ctx.E), "mature": len(ctx.EM)}


def fmt_number(x, lang: str, decimals: int = 0) -> str:
    """7,691 · 69.9 in English; 7.691 · 69,9 in Spanish (the README convention since F0)."""
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "#").replace(".", ",").replace("#", ".") if lang == "es" else s


def fmt_value(r: dict, lang: str) -> str:
    """Display value: rates as %, durations in hours or days (from the KPI id), amounts in EUR, counts as integers."""
    if r["status"] != "available":
        return ("not available" if lang == "en" else "no disponible") + f" ({r['reason']})"
    v = r["value"]
    if r["kind"] == "count":
        return fmt_number(v, lang)
    if r["kind"] == "rate":
        return fmt_number(100 * v, lang, 1) + " %"
    if r["id"].endswith("_eur"):
        return ("€" + fmt_number(v, lang)) if lang == "en" else (fmt_number(v, lang) + " €")
    unit = "h" if r["id"].endswith("_hours") else ("days" if lang == "en" else "días")
    return fmt_number(v, lang, 1) + f" {unit}"


def fmt_base(r: dict, lang: str) -> str:
    n, d = r.get("numerator_value"), r.get("denominator_value")
    if r["status"] != "available":
        return "—"
    if n is not None and d is not None:
        return f"{fmt_number(n, lang)} / {fmt_number(d, lang)}"
    if d is not None:
        return "n = " + fmt_number(d, lang)
    return "—"


# A selection of the 47 reference metrics shown in the README (values always computed, never typed by hand)
REFERENCE_IDS = ["held_rate_manual_route", "held_rate_bot_route", "show_rate_per_lead", "enrollments_over_interviews_held",
                 "sla_first_attempt_24h_manual", "sla_first_attempt_24h_manual_weekday", "followup_48h_manual_advisor",
                 "open_leads_at_snapshot", "open_without_next_task", "avg_net_price_eur"]


def _table(rows_in: list[dict], lang: str, first: str, with_base: bool = True) -> str:
    """with_base=False leaves out numerators and denominators: the README quotes only figures the notebook shows
    (tests/test_notebook_presentation.py); show_results.py prints them all."""
    base_col = (" Numerator / denominator |" if lang == "en" else " Numerador / denominador |") if with_base else ""
    head = (f"| {first} | Value |{base_col} Population (unit) | Time basis |" if lang == "en" else
            f"| {first} | Valor |{base_col} Población (unidad) | Base temporal |")
    rows = [head, "|---|---|" + ("---|" if with_base else "") + "---|---|"]
    for r in rows_in:
        label = r["label_en"] if lang == "en" else r["label_es"]
        unit = f" ({r['unit']})" if r.get("unit") else ""
        base = f" {fmt_base(r, lang)} |" if with_base else ""
        value = r.get("display") or fmt_value(r, lang)
        if r.get("display_base") and not with_base:
            value += f" ({fmt_base(r, lang)})"
        rows.append(f"| {label} | {value} |{base} {r['population']}{unit} | {r['time_basis']} |")
    return "\n".join(rows) + "\n"


def reference_rows(res: dict) -> list[dict]:
    live = {m["id"]: m for m in res["live47"]}
    rows = [{**live[i], "status": "available" if live[i]["value"] is not None else "not_available", "reason": "—"}
            for i in REFERENCE_IDS]
    for r in rows:   # follow-up: the complete-window base is part of the figure (as in the README since F0)
        if r["id"] == "followup_48h_manual_advisor":
            r["display_base"] = True
    real, exp = live["advisor_months_over_150_realised"], live["advisor_months_over_150_expected"]
    rows.append({**real, "status": "available", "display": f"{real['value']} / {exp['value']}",
                 "label_en": "Advisor-months above 150 leads (realised / expected before randomness)",
                 "label_es": "Meses-asesor por encima de 150 leads (realizados / esperados antes del azar)",
                 "population": f"{real['population']} / {exp['population']}"})
    return rows


def _note(res: dict, lang: str) -> str:
    counts = (f"Eligible leads {fmt_number(res['eligible'], 'en')} · mature eligible leads {fmt_number(res['mature'], 'en')}. "
              if lang == "en" else
              f"Leads elegibles {fmt_number(res['eligible'], 'es')} · leads elegibles maduros {fmt_number(res['mature'], 'es')}. ")
    return counts + (f"Snapshot {res['snapshot']}. {SYNTHETIC['en']} Population and time-basis definitions are quoted from the "
            f"reference engine (English)." if lang == "en" else
            f"Fecha de corte {res['snapshot']}. {SYNTHETIC['es']} Las definiciones de población y base temporal se citan "
            f"del motor de referencia (en inglés).")


def results_table(res: dict, lang: str) -> str:
    """The eight KPIs (declarative engine) with value, numerator / denominator, population and time basis."""
    return _table(res["eight"], lang, "KPI") + "\n" + _note(res, lang) + "\n"


def reference_table(res: dict, lang: str, with_base: bool = True) -> str:
    return _table(reference_rows(res), lang, "Metric" if lang == "en" else "Métrica", with_base)


def readme_block(res: dict, lang: str) -> str:
    sub = ("**Eight KPIs of the declarative engine** (identical to the reference engine)" if lang == "en" else
           "**Ocho KPIs del motor declarativo** (idénticos al motor de referencia)")
    sub2 = ("**Selected metrics of the reference engine** (12 of 47)" if lang == "en" else
            "**Selección de métricas del motor de referencia** (12 de 47)")
    tail = ("Numerators and denominators of every figure: `python scripts/show_results.py --all`." if lang == "en" else
            "Numeradores y denominadores de cada cifra: `python scripts/show_results.py --all --lang es`.")
    # blank lines around the markers: every Markdown renderer then treats the comments as separate blocks
    return (f"{RESULTS_START}\n\n{sub}\n\n{_table(res['eight'], lang, 'KPI', with_base=False)}\n{sub2}\n\n"
            f"{reference_table(res, lang, with_base=False)}\n{_note(res, lang)} {tail}\n\n{RESULTS_END}")


def readme_problems(res: dict) -> list[str]:
    probs = []
    for lang, name in (("en", "README.md"), ("es", "README.es.md")):
        text = (ROOT / name).read_text(encoding="utf-8")
        if readme_block(res, lang) not in text:
            probs.append(f"{name}: results block differs from the computed results")
    return probs


# --------------------------------------------------------------------------- #
# Internal links
# --------------------------------------------------------------------------- #
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")
DOCS_WITH_LINKS = ["README.md", "README.es.md", "CHANGELOG.md", "docs/analytical_decisions.md",
                   "docs/analytical_decisions.es.md", "docs/PROJECT_STATUS.md", "docs/PROJECT_STATUS.es.md"]


# Written at the end of scripts/release_run.py (links to them are checked there, after writing)
RELEASE_OUTPUTS = {"reports/release/MANIFEST_RELEASE.sha256", "reports/release/RELEASE_REPORT.md",
                   "reports/release/RELEASE_REPORT.es.md", "reports/release/F3_COMPARISON.md",
                   "reports/release/F3_COMPARISON.es.md"}


def link_problems(files=DOCS_WITH_LINKS) -> tuple[list[str], int]:
    """Relative links and images must point to existing files, or to a file written by the release run
    (RELEASE_OUTPUTS). External (http/https/mailto) links are not fetched."""
    probs, checked = [], 0
    for rel in files:
        base = (ROOT / rel).parent
        for m in LINK.finditer((ROOT / rel).read_text(encoding="utf-8")):
            target = m.group(1) or m.group(2)
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            checked += 1
            path = target.split("#", 1)[0]
            resolved = (base / path).resolve()
            rel_target = resolved.relative_to(ROOT).as_posix() if resolved.is_relative_to(ROOT) else None
            if not resolved.exists() and rel_target not in RELEASE_OUTPUTS:
                probs.append(f"{rel}: broken link {target}")
    return probs, checked


# --------------------------------------------------------------------------- #
# Security scan (patterns; not a guarantee)
# --------------------------------------------------------------------------- #
_P = lambda *parts: "".join(parts)   # build patterns from parts so this file does not match itself
SCAN_PATTERNS = {
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"),
    "phone number": re.compile(r"(?<![\w.])\+\d{1,3}[ .-]?\d{2,4}[ .-]?\d{3}[ .-]?\d{3,4}(?![\w.])|(?<![\w.])\d{3}[ .-]\d{3}[ .-]\d{3}(?![\w.])"),
    "private key": re.compile(_P("-----BEGIN ", r"[A-Z ]*", "PRIVATE KEY-----")),
    "cloud or API token": re.compile(_P("AKI", r"A[0-9A-Z]{16}") + "|" + _P("gh", r"[pousr]_[A-Za-z0-9]{30,}") + "|"
                                     + _P("s", r"k-[A-Za-z0-9]{20,}") + "|" + _P("xo", r"x[abprs]-[A-Za-z0-9-]{10,}")),
    "credential assignment": re.compile(r"(?i)\b(api[_-]?key|secret|passw(?:or)?d|token|bearer)\b\s*[:=]\s*['\"][^'\"\s]{6,}['\"]"),
    "local absolute path": re.compile(_P("/ho", "me/[A-Za-z]") + "|" + _P("/Use", "rs/[A-Za-z]") + "|" + _P("[A-Za-z]:", r"\\\\?Users")
                                      + "|" + _P("/ro", "ot/") + "|" + _P("/t", "mp/") + "|" + _P("fi", "le://")),
}
PERSONAL_COLUMNS = re.compile(r"(?i)(first_?name|last_?name|full_?name|surname|email|e_mail|phone|mobile|dni|nie|nif|passport|address|iban|birth)")
# Column names that match PERSONAL_COLUMNS but hold no personal data (values checked in v1.4.0-gh; the scan also
# verifies the values stay inside this domain).
REVIEWED_COLUMNS = {"email_status": {"sent", "not_sent", "failed", ""}}   # delivery status of a synthetic email
SCAN_SELF = {"scripts/release_checks.py"}            # holds the pattern definitions


BINARY_SUFFIXES = (".png", ".otf")


def is_binary(rel: str, data: bytes) -> bool:
    """Images and fonts, or any file with a NUL byte in its first 4 KiB."""
    return rel.endswith(BINARY_SUFFIXES) or b"\x00" in data[:4096]


def security_scan() -> dict:
    """Pattern scan of every repository text file, the CSV headers and the executed notebook."""
    findings, scanned, skipped_binary = [], 0, []
    for rel, p in repo_files():
        if rel in SCAN_SELF:
            continue
        data = p.read_bytes()
        if is_binary(rel, data):
            skipped_binary.append(rel)
            continue
        text = data.decode("utf-8", errors="replace")
        scanned += 1
        for name, pat in SCAN_PATTERNS.items():
            for m in pat.finditer(text):
                findings.append({"file": rel, "kind": name, "match": m.group(0)[:40]})
        if rel.endswith(".csv"):
            header = text.split("\n", 1)[0].split(",")
            for col in header:
                if not PERSONAL_COLUMNS.search(col):
                    continue
                if col in REVIEWED_COLUMNS:
                    values = {row[col] for row in csv.DictReader(io.StringIO(text))}
                    if values <= REVIEWED_COLUMNS[col]:
                        continue
                findings.append({"file": rel, "kind": "personal-data column name", "match": col})
    nb = json.loads((ROOT / "notebooks" / "admissions_analysis.ipynb").read_text(encoding="utf-8"))
    outs = [o for c in nb["cells"] if c["cell_type"] == "code" for o in c.get("outputs", [])]
    nb_info = {"metadata_keys": sorted(nb["metadata"]),
               "cell_metadata_keys": sorted({k for c in nb["cells"] for k in c.get("metadata", {})}),
               "outputs": len(outs), "errors": sum(o["output_type"] == "error" for o in outs),
               "stderr": sum(o.get("name") == "stderr" for o in outs),
               "images": sum("image/png" in o.get("data", {}) for o in outs)}
    if nb_info["metadata_keys"] != ["kernelspec", "language_info"]:
        findings.append({"file": "notebooks/admissions_analysis.ipynb", "kind": "notebook metadata", "match": str(nb_info["metadata_keys"])})
    if nb_info["errors"] or nb_info["stderr"]:
        findings.append({"file": "notebooks/admissions_analysis.ipynb", "kind": "notebook error/stderr output", "match": ""})
    if nb_info["cell_metadata_keys"]:
        findings.append({"file": "notebooks/admissions_analysis.ipynb", "kind": "cell metadata", "match": str(nb_info["cell_metadata_keys"])})
    return {"findings": findings, "text_files_scanned": scanned, "binary_files_not_scanned": skipped_binary,
            "notebook": nb_info, "patterns": list(SCAN_PATTERNS) + ["personal-data column name", "notebook metadata/errors"],
            "reviewed_columns": {k: sorted(v - {""}) for k, v in REVIEWED_COLUMNS.items()},
            "excluded": sorted(SCAN_SELF)}


# --------------------------------------------------------------------------- #
# Notebook comparison (v1.4.3-gh): analytical (portable) vs graphical (strict)
# --------------------------------------------------------------------------- #
# Volatile notebook fields that may differ between machines. None is allowed: scripts/build_notebook.py already strips
# execution timings, so every byte other than the PNG payloads must match the reference notebook.
ALLOWED_VOLATILE: frozenset = frozenset()


def _png_size(b64) -> tuple[int, int] | None:
    import base64
    try:
        raw = base64.b64decode("".join(b64) if isinstance(b64, list) else b64)
    except Exception:  # noqa: BLE001
        return None
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")


def compare_notebooks(rebuilt: dict, reference: dict) -> dict:
    """Walk both notebook JSON documents together. A difference whose path ends in data/image/png is graphical; any
    other difference (code, text or HTML outputs, numbers, execution counts, metadata, structure) is analytical.

    Returns {"png": [{"cell", "output", "reference_size", "rebuilt_size"}], "other": [paths]}."""
    png, other = [], []

    def walk(a, b, path):
        if len(path) >= 2 and path[-2:] == ("data", "image/png"):
            if a != b:
                png.append({"cell": path[1], "output": path[3] if len(path) > 3 else None,
                            "reference_size": _png_size(b), "rebuilt_size": _png_size(a)})
            return
        if path and path[-1] in ALLOWED_VOLATILE:
            return
        if type(a) is not type(b):
            other.append("/".join(map(str, path)) or "<root>")
        elif isinstance(a, dict):
            for k in sorted(set(a) | set(b)):
                if k not in a or k not in b:
                    other.append("/".join(map(str, path + (k,))))
                else:
                    walk(a[k], b[k], path + (k,))
        elif isinstance(a, list):
            if len(a) != len(b):
                other.append("/".join(map(str, path)) + f" (length {len(a)} vs {len(b)})")
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path + (i,))
        elif a != b:
            other.append("/".join(map(str, path)))

    walk(rebuilt, reference, ())
    return {"png": png, "other": other}


def notebook_outcome(mode: str, rebuilt_bytes: bytes, reference_bytes: bytes) -> dict:
    """strict: the rebuilt notebook must be byte-identical to the reference.
    portable: every analytical part must be identical; PNG payloads may differ and are reported separately."""
    if rebuilt_bytes == reference_bytes:
        return {"ok": True, "identical": True, "png": [], "other": []}
    try:
        cmp = compare_notebooks(json.loads(rebuilt_bytes.decode("utf-8")), json.loads(reference_bytes.decode("utf-8")))
    except ValueError as exc:
        return {"ok": False, "identical": False, "png": [], "other": [f"not a readable notebook: {exc}"]}
    if not cmp["png"] and not cmp["other"]:
        cmp["other"] = ["serialisation differs (same JSON content, different bytes)"]
    ok = (mode == "portable") and not cmp["other"]
    return {"ok": ok, "identical": False, **cmp}


def render_environment() -> dict:
    """Versions that affect chart rendering on this machine (recorded, not used to decide anything)."""
    import platform
    info = {"system": f"{platform.system()} {platform.release()} {platform.machine()}", "python": platform.python_version()}
    try:
        import matplotlib
        from matplotlib import ft2font
        info["matplotlib"] = matplotlib.__version__
        info["freetype"] = f"{ft2font.__freetype_version__} ({ft2font.__freetype_build_type__} build)"
    except Exception as exc:  # noqa: BLE001
        info["matplotlib"] = f"unavailable: {exc}"
    for mod in ("numpy", "PIL"):
        try:
            info[mod if mod != "PIL" else "pillow"] = __import__(mod).__version__
        except Exception:  # noqa: BLE001
            pass
    import os
    for var in ("FREETYPE_PROPERTIES", "MATPLOTLIBRC", "MPLBACKEND"):   # recorded only when set
        if os.environ.get(var):
            info[f"env {var}"] = os.environ[var]
    fonts = ROOT / "assets" / "fonts" / "inter"
    info["project_fonts"] = {p.name: __import__("hashlib").sha256(p.read_bytes()).hexdigest()[:16]
                             for p in sorted(fonts.glob("*.otf"))}
    return info


# The environment where the frozen F1 notebook images were rendered (and where strict mode is verified).
REFERENCE_RENDER_ENVIRONMENT = {"system": "Linux x86_64", "python": "3.13.16", "matplotlib": "3.11.2",
                                "freetype": "2.14.3 (local build)", "numpy": "2.5.3", "pillow": "12.3.0",
                                "project_fonts": "Inter-Regular.otf be6d709dcb730ddaf…, Inter-Bold.otf 00fd6f4691ee8884…"}
