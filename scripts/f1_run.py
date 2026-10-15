"""F1 clean run and comparison with the frozen F0 reference (v1.0.0-f0).

Ejecución limpia de F1 y comparación con la referencia congelada de F0.

Steps (real subprocesses; exit codes and durations are recorded):
  0. environment   compare installed versions with baseline/environment.txt
  1. clean         remove data/, the executed notebook, reports/f1/ and caches (never touches baseline/)
  2. generate      python src/generate_data.py; the CSV hashes must equal the F0 manifest
  3. notebook      python scripts/build_notebook.py (fresh kernel)
  4. export        python scripts/export_metrics.py -> reports/f1/metrics_f1.json
  5. tests         python -m pytest -q
  6. compare       classify every file against baseline/MANIFEST.sha256: unchanged / modified (declared) /
                   new (declared); anything else fails. baseline/ must be byte-identical before and after the run.
  7. reconcile     47 metrics of reports/f1/metrics_f1.json vs baseline/metrics_v1.json
  8. outputs       reports/f1/MANIFEST_F1.sha256, F1_REPORT(.es).md, F0_COMPARISON(.es).md

Usage:
  python scripts/f1_run.py          # create / refresh the F1 manifest and reports
  python scripts/f1_run.py --check  # same clean run, then require the stored F1 manifest (exit 1 on drift)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "f1"
VERSION_ID = "v1.1.0-f1"
F0_ID = "v1.0.0-f0"
F0_TREE_ID = "eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df"
F0_FROZEN_OUTSIDE_MANIFEST = {
    "baseline/MANIFEST.sha256": F0_TREE_ID,
    "baseline/F0_REPORT.md": "573dc315e20b5cbbc1268952209b06eb1ef549fcf200f95ac38920ba4156c84f",
    "baseline/F0_REPORT.es.md": "418a2a5a2cd59e031493ae64f31a5da40193af18c35f9e44e9daf10a8939daec",
}
DECLARED_MODIFIED = {
    "scripts/build_notebook.py": "notebook cells now call src/metrics.py; no longer writes baseline/",
    "notebooks/admissions_analysis.ipynb": "rebuilt from the new cells (same values; different code and layout)",
    "README.md": "repository structure, how to run, source of truth (no figure changed)",
    "README.es.md": "estructura, cómo ejecutar, fuente de verdad (ninguna cifra cambia)",
    "scripts/f0_baseline.py": "guard only: refuses to run on the F1 tree",
}
DECLARED_NEW = {
    "src/metrics.py", "scripts/export_metrics.py", "scripts/f1_run.py", "tests/test_metrics_unit.py",
    "tests/test_regression_f0.py", "tests/test_notebook_presentation.py", "reports/f1/metrics_f1.json",
}
REPORT_FILES = {"reports/f1/MANIFEST_F1.sha256", "reports/f1/F1_REPORT.md", "reports/f1/F1_REPORT.es.md",
                "reports/f1/F0_COMPARISON.md", "reports/f1/F0_COMPARISON.es.md"}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".git"}
PKGS = ["numpy", "pandas", "pyyaml", "matplotlib", "nbformat", "nbconvert", "ipykernel", "pytest"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_files():
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not any(part in EXCLUDE_DIRS for part in p.parts):
            yield p.relative_to(ROOT).as_posix(), p


def baseline_hashes():
    return {rel: sha(p) for rel, p in tree_files() if rel.startswith("baseline/")}


def run(name, cmd, log):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "running over TCP" not in l)
    log.append({"step": name, "cmd": " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)),
                "exit": p.returncode, "secs": round(time.time() - t0, 1), "out": out.strip()})
    print(f"[{name}] exit={p.returncode} ({log[-1]['secs']} s)")
    if p.returncode != 0:
        print(out)
        raise SystemExit(f"step {name} failed")
    return out


def environment():
    found = {"python": platform.python_version()}
    for pkg in PKGS:
        try:
            found[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            found[pkg] = "(not installed)"
    recorded = dict(l.split("==", 1) for l in (ROOT / "baseline" / "environment.txt").read_text().split())
    diffs = {k: (recorded.get(k), v) for k, v in found.items() if recorded.get(k) != v}
    return found, diffs


def clean(log):
    t0, removed = time.time(), []
    for rel in ("data", "notebooks/admissions_analysis.ipynb", "reports/f1", ".pytest_cache"):
        p = ROOT / rel
        if p.is_dir():
            shutil.rmtree(p); removed.append(rel + "/")
        elif p.exists():
            p.unlink(); removed.append(rel)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    log.append({"step": "clean", "cmd": "remove " + ", ".join(removed), "exit": 0,
                "secs": round(time.time() - t0, 1), "out": ""})
    print("[clean] removed:", ", ".join(removed))


def f0_manifest():
    rows = (ROOT / "baseline" / "MANIFEST.sha256").read_text().strip().splitlines()
    return {p: h for h, p in (r.split("  ", 1) for r in rows)}


def classify():
    man = f0_manifest()
    now = {rel: sha(p) for rel, p in tree_files()}
    rows, problems = [], []
    for rel in sorted(set(man) | set(now) | set(F0_FROZEN_OUTSIDE_MANIFEST)):
        if rel in REPORT_FILES:
            continue
        ref = man.get(rel) or F0_FROZEN_OUTSIDE_MANIFEST.get(rel)
        cur = now.get(rel)
        if ref and cur == ref:
            status = "unchanged"
        elif ref and cur is None:
            status = "REMOVED"; problems.append(rel)
        elif ref and rel in DECLARED_MODIFIED:
            status = "modified (declared)"
        elif ref:
            status = "MODIFIED (undeclared)"; problems.append(rel)
        elif rel in DECLARED_NEW:
            status = "new (declared)"
        else:
            status = "NEW (undeclared)"; problems.append(rel)
        rows.append({"file": rel, "status": status, "f0": ref, "f1": cur})
    return rows, problems


def f1_manifest():
    lines = [f"{sha(p)}  {rel}" for rel, p in tree_files() if rel not in REPORT_FILES]
    text = "\n".join(lines) + "\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def parse_pytest(out):
    m = re.search(r"(\d+) passed(?:, (\d+) failed)?.* in ([\d.]+)s", out)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, -1)


def write_reports(log, env, env_diffs, rows, rec, tree_id, check_result, base_before, base_after):
    when = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    passed, failed = parse_pytest(next(s["out"] for s in log if s["step"] == "tests"))
    nb_line = next(s["out"] for s in log if s["step"] == "notebook").splitlines()[-1]
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    matching = int(rec.match.astype(bool).sum())
    for lang in ("en", "es"):
        es = lang == "es"
        T = (lambda e, s: s) if es else (lambda e, s: e)
        steps = "\n".join(f"| {i + 1} | `{s['cmd']}` | {s['exit']} | {s['secs']} |" for i, s in enumerate(log))
        envtxt = ", ".join(f"{k}=={v}" for k, v in env.items())
        envchk = (T("identical to baseline/environment.txt", "idéntico a baseline/environment.txt") if not env_diffs else
                  T("DIFFERENT from baseline/environment.txt: ", "DISTINTO de baseline/environment.txt: ") + str(env_diffs))
        status_rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(counts.items()))
        chk = check_result[lang] if check_result else T("not run in this mode (use --check)", "no ejecutada en este modo (usar --check)")
        report = f"""{T('**Language:** English | [Español](F1_REPORT.es.md)', '**Idioma:** [English](F1_REPORT.md) | Español')}

# {T('F1 — run report', 'F1 — informe de ejecución')} (`{VERSION_ID}`)

{T('Generated by', 'Generado por')} `python scripts/f1_run.py{' --check' if check_result else ''}` · {when}.
{T('All data and figures are synthetic (seed 42). Scope: admissions profile only; no portability claim.',
   'Todos los datos y cifras son sintéticos (semilla 42). Alcance: solo el perfil de admisiones; sin afirmaciones de portabilidad.')}

## {T('Version', 'Versión')}

| {T('Item', 'Elemento')} | {T('Value', 'Valor')} |
|---|---|
| {T('F1 id', 'Identificador F1')} | `{VERSION_ID}` |
| {T('F1 tree id (SHA-256 of', 'Tree id F1 (SHA-256 de')} `reports/f1/MANIFEST_F1.sha256`) | `{tree_id}` |
| {T('Reference', 'Referencia')} | `{F0_ID}` · {T('F0 tree id', 'tree id F0')} `{F0_TREE_ID}` |
| Git | {T('no commit or tag (not a git repository; not authorised)', 'sin commit ni tag (no es un repositorio git; no autorizado)')} |
| {T('Environment', 'Entorno')} | {envtxt} — {envchk} |

## {T('Commands and results', 'Comandos y resultados')}

| # | {T('Command', 'Comando')} | exit | {T('seconds', 'segundos')} |
|---|---|---|---|
{steps}

| {T('Check', 'Comprobación')} | {T('Result', 'Resultado')} |
|---|---|
| {T('Notebook (fresh kernel)', 'Notebook (kernel nuevo)')} | {nb_line} |
| {T('Tests', 'Pruebas')} | **{passed} passed, {failed} failed** |
| {T('47 metrics vs F0', '47 métricas frente a F0')} | **{matching} / {len(rec)}** {T('match (ids, order, descriptive fields, numerators, denominators, values at 6 decimals)', 'coinciden (ids, orden, campos descriptivos, numeradores, denominadores, valores a 6 decimales)')} |
| {T('baseline/ before vs after the run', 'baseline/ antes y después de la ejecución')} | {T('byte-identical', 'idéntica byte a byte') if base_before == base_after else T('CHANGED', 'CAMBIADA')} ({len(base_after)} {T('files', 'archivos')}) |
| {T('F1 reproducibility', 'Reproducibilidad de F1')} | {chk} |

## {T('Files compared with the F0 manifest', 'Archivos comparados con el manifiesto F0')}

| {T('Status', 'Estado')} | {T('Files', 'Archivos')} |
|---|---|
{status_rows}

{T('Details per file, with both hashes:', 'Detalle por archivo, con ambos hashes:')} [`F0_COMPARISON{'.es' if es else ''}.md`](F0_COMPARISON{'.es' if es else ''}.md).
"""
        (OUT / ("F1_REPORT.es.md" if es else "F1_REPORT.md")).write_text(report, encoding="utf-8")

        frow = "\n".join(f"| `{r['file']}` | {r['status']} | `{(r['f0'] or '—')[:16]}` | `{(r['f1'] or '—')[:16]}` | "
                         f"{DECLARED_MODIFIED.get(r['file'], '') if r['status'].startswith('modified') else ''} |" for r in rows)
        mrow = "\n".join(
            f"| `{i}` | {r.value_reference} | {r.value} | {r.abs_diff if r.abs_diff is not None else '—'} | "
            f"{r.numerator_reference if r.numerator_reference is not None else '—'} / {r.numerator if r.numerator is not None else '—'} | "
            f"{r.denominator_reference if r.denominator_reference is not None else '—'} / {r.denominator if r.denominator is not None else '—'} | "
            f"{'✓' if r.descriptive_equal else '✗'} | {'✓' if r.match else '✗'} |" for i, r in rec.iterrows())
        comp = f"""{T('**Language:** English | [Español](F0_COMPARISON.es.md)', '**Idioma:** [English](F0_COMPARISON.md) | Español')}

# {T('F1 vs F0 — file and metric comparison', 'F1 frente a F0 — comparación de archivos y métricas')}

{T('Reference', 'Referencia')}: `{F0_ID}` (`baseline/MANIFEST.sha256`, tree id `{F0_TREE_ID}`). {T('Hashes shown truncated to 16 characters.', 'Hashes truncados a 16 caracteres.')}

## {T('Files', 'Archivos')}

| {T('File', 'Archivo')} | {T('Status', 'Estado')} | SHA-256 F0 | SHA-256 F1 | {T('Declared change', 'Cambio declarado')} |
|---|---|---|---|---|
{frow}

## {T('47 metrics', '47 métricas')} — {matching} / {len(rec)} {T('match', 'coinciden')}

{T('Values compared at the reference rounding of 6 decimals with no extra tolerance; numerators, denominators and descriptive fields (labels, unit, kind, population, numerator, denominator, time basis, definition reference) must be equal.',
   'Valores comparados al redondeo de la referencia (6 decimales) sin tolerancia adicional; numeradores, denominadores y campos descriptivos (etiquetas, unidad, tipo, población, numerador, denominador, base temporal, referencia de definición) deben ser iguales.')}

| {T('Metric', 'Métrica')} | F0 | F1 | {T('abs. diff.', 'dif. abs.')} | {T('numerator F0 / F1', 'numerador F0 / F1')} | {T('denominator F0 / F1', 'denominador F0 / F1')} | {T('descriptive', 'descriptivos')} | {T('match', 'coincide')} |
|---|---|---|---|---|---|---|---|
{mrow}
"""
        (OUT / ("F0_COMPARISON.es.md" if es else "F0_COMPARISON.md")).write_text(comp, encoding="utf-8")


def main():
    # Guard (added in F2): this tool deletes and rewrites reports/f1/, which is frozen since F2.
    if (ROOT / "src" / "canonical").exists():
        raise SystemExit("f1_run.py only runs on the F1 tree (v1.1.0-f1); this tree is F2 or later and reports/f1/ is frozen.\n"
                         "Verify F1 from admissions-crm-analytics-v1.1.0-f1.zip in a clean folder; verify F2 with scripts/f2_run.py.")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stored = (OUT / "MANIFEST_F1.sha256").read_text() if (OUT / "MANIFEST_F1.sha256").exists() else None
    if args.check and stored is None:
        raise SystemExit("no stored reports/f1/MANIFEST_F1.sha256 to check against")
    env, env_diffs = environment()
    print("[environment]", "matches baseline/environment.txt" if not env_diffs else f"DIFFERS: {env_diffs}")
    base_before = baseline_hashes()

    log = []
    clean(log)
    run("generate", [sys.executable, "src/generate_data.py"], log)
    man = f0_manifest()
    bad = [p for p in ("data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv") if sha(ROOT / p) != man[p]]
    if bad:
        raise SystemExit(f"generated data differ from F0: {bad}")
    run("notebook", [sys.executable, "scripts/build_notebook.py"], log)
    run("export", [sys.executable, "scripts/export_metrics.py"], log)
    run("tests", [sys.executable, "-m", "pytest", "-q"], log)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)

    rows, problems = classify()
    base_after = baseline_hashes()
    sys.path.insert(0, str(ROOT / "src"))
    import metrics
    rec = metrics.reconcile(json.loads((OUT / "metrics_f1.json").read_text(encoding="utf-8")),
                            json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8")))
    text, tree_id = f1_manifest()
    check_result = None
    if args.check:
        old = {p: h for h, p in (l.split("  ", 1) for l in stored.strip().splitlines())}
        new = {p: h for h, p in (l.split("  ", 1) for l in text.strip().splitlines())}
        diff = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        check_result = ({"en": f"identical to the stored F1 manifest ({len(new)} files) — tree id {tree_id[:16]}",
                         "es": f"idéntica al manifiesto F1 guardado ({len(new)} archivos) — tree id {tree_id[:16]}"}
                        if not diff else {"en": "DRIFT in: " + ", ".join(diff), "es": "DIFERENCIAS en: " + ", ".join(diff)})
        print("[check]", check_result["en"])
        (OUT / "MANIFEST_F1.sha256").write_text(stored, encoding="utf-8")   # keep the stored reference (clean removed it)
    else:
        (OUT / "MANIFEST_F1.sha256").write_text(text, encoding="utf-8")
    write_reports(log, env, env_diffs, rows, rec, tree_id, check_result, base_before, base_after)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    print(f"[compare] {len(rows)} files · problems: {problems or 'none'} · baseline/ unchanged: {base_before == base_after}")
    print(f"[reconcile] {int(rec.match.astype(bool).sum())} / {len(rec)} metrics match F0")
    print(f"F1 {VERSION_ID} · tree id {tree_id}")
    if problems or base_before != base_after or not bool(rec.match.astype(bool).all()) or \
            (check_result and check_result["en"].startswith("DRIFT")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
