"""F0 baseline: clean run + verifiable freeze of v1.

Línea base F0: ejecución limpia y congelación verificable de la v1.

Steps (each one a real subprocess; exit codes and durations are recorded):
  1. clean       remove data/, caches, the executed notebook and baseline/metrics_v1.json
  2. generate    python src/generate_data.py
  3. notebook    python scripts/build_notebook.py   (fresh kernel; writes baseline/metrics_v1.json)
  4. tests       python -m pytest -q                 (integrity + baseline tests)
  5. manifest    SHA-256 of every repository file -> baseline/MANIFEST.sha256; tree id = SHA-256 of the manifest
  6. report      baseline/F0_REPORT.md and baseline/F0_REPORT.es.md

Usage:
  python scripts/f0_baseline.py          # create / refresh the baseline
  python scripts/f0_baseline.py --check  # same clean run, then compare with the stored manifest (exit 1 on drift)
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
BASE = ROOT / "baseline"
BASELINE_ID = "v1.0.0-f0"
# Files excluded from the manifest: the manifest itself, run reports (they contain timings), caches.
EXCLUDE = {"baseline/MANIFEST.sha256", "baseline/F0_REPORT.md", "baseline/F0_REPORT.es.md"}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".git"}
PKGS = ["numpy", "pandas", "pyyaml", "matplotlib", "nbformat", "nbconvert", "ipykernel", "pytest"]


def run(name, cmd, log):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "running over TCP" not in l)
    log.append({"step": name, "cmd": " ".join(cmd), "exit": p.returncode, "secs": round(time.time() - t0, 1),
                "out": out.strip()})
    print(f"[{name}] exit={p.returncode} ({log[-1]['secs']} s)")
    if p.returncode != 0:
        print(out)
        raise SystemExit(f"step {name} failed")
    return out


def clean(log):
    t0 = time.time()
    removed = []
    for rel in ("data", "notebooks/admissions_analysis.ipynb", "baseline/metrics_v1.json", ".pytest_cache"):
        p = ROOT / rel
        if p.is_dir():
            shutil.rmtree(p); removed.append(rel + "/")
        elif p.exists():
            p.unlink(); removed.append(rel)
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d); removed.append(str(d.relative_to(ROOT)) + "/")
    log.append({"step": "clean", "cmd": "remove " + ", ".join(removed), "exit": 0,
                "secs": round(time.time() - t0, 1), "out": ""})
    print("[clean] removed:", ", ".join(removed))


def manifest():
    rows = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_dir() or rel in EXCLUDE or any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
    text = "\n".join(rows) + "\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def environment():
    lines = [f"python=={platform.python_version()}"]
    for pkg in PKGS:
        try:
            lines.append(f"{pkg}=={md.version(pkg)}")
        except md.PackageNotFoundError:
            lines.append(f"{pkg}==(not installed)")
    return "\n".join(lines) + "\n"


def followup_audit():
    sys.path.insert(0, str(ROOT / "src"))
    import checks
    import pandas as pd
    L, A, _ = checks.load(ROOT / "data")
    r = checks.followup_within_48h(L, A)
    snap, w = L.snapshot_date.iloc[0], pd.Timedelta(hours=48)
    E = L[~L.is_duplicate & ~L.is_reactivation]
    held = E[E.entered_interview_held_at.notna()]
    H = held[held.entered_interview_held_at + w <= snap]
    adv = A[(A.actor_type == "advisor") & (A.direction == "outbound") & A.activity_type.isin(["call", "whatsapp"])
            & ~A.is_automated.astype(bool)].merge(H[["lead_id", "entered_interview_held_at"]], on="lead_id")
    d = adv.activity_at - adv.entered_interview_held_at
    first = adv.sort_values("activity_at").groupby("lead_id").head(1)
    wrong = int(((first.activity_at - first.entered_interview_held_at) <= w).sum())
    return {"held": len(held), "excluded_open_window": len(held) - len(H), "denominator": r["denominator"],
            "numerator": r["numerator"], "rate": r["rate"], "in_window": int(((d > pd.Timedelta(0)) & (d <= w)).sum()),
            "at_interview": int((d == pd.Timedelta(0)).sum()), "before": int((d < pd.Timedelta(0)).sum()),
            "after_48h": int((d > w).sum()), "wrong_rule": wrong}


def parse_pytest(out):
    m = re.search(r"(\d+) passed(?:, (\d+) failed)?.* in ([\d.]+)s", out)
    return (int(m.group(1)), int(m.group(2) or 0), float(m.group(3))) if m else (0, -1, 0.0)


def write_reports(log, tree_id, env, audit, metrics, check_result):
    passed, failed, _ = parse_pytest(next(s["out"] for s in log if s["step"] == "tests"))
    nb_line = next(s["out"] for s in log if s["step"] == "notebook").splitlines()[-1]
    gen_line = next(s["out"] for s in log if s["step"] == "generate").splitlines()[-1]
    when = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    hashes = metrics["inputs_sha256"]
    for lang in ("en", "es"):
        es = lang == "es"
        T = (lambda e, s: s) if es else (lambda e, s: e)
        rows = "\n".join(f"| {i + 1} | `{s['cmd']}` | {s['exit']} | {s['secs']} |" for i, s in enumerate(log))
        hrows = "\n".join(f"| `{k}` | `{v}` |" for k, v in hashes.items())
        a = audit
        pct = (lambda x: f"{x * 100:.1f} %".replace(".", ",")) if es else (lambda x: f"{x * 100:.1f} %")
        num = (lambda n: f"{n:,}".replace(",", ".")) if es else (lambda n: f"{n:,}")
        text = f"""{T('**Language:** English | [Español](F0_REPORT.es.md)', '**Idioma:** [English](F0_REPORT.md) | Español')}

# {T('F0 baseline — run report', 'Línea base F0 — informe de ejecución')}

{T('Generated by', 'Generado por')} `python scripts/f0_baseline.py{' --check' if check_result else ''}` · {when}.
{T('All data and figures are synthetic (seed 42).', 'Todos los datos y cifras son sintéticos (semilla 42).')}

## {T('Frozen version', 'Versión congelada')}

| {T('Item', 'Elemento')} | {T('Value', 'Valor')} |
|---|---|
| {T('Baseline id', 'Identificador')} | `{BASELINE_ID}` |
| {T('Tree id (SHA-256 of', 'Tree id (SHA-256 de')} `baseline/MANIFEST.sha256`) | `{tree_id}` |
| {T('Git commit / tag', 'Commit / tag de git')} | {T('none — the folder is not a git repository and no commit was made (as instructed)', 'ninguno — la carpeta no es un repositorio git y no se ha hecho ningún commit (según lo indicado)')} |
| {T('Environment', 'Entorno')} | {', '.join(env.strip().splitlines())} |

## {T('Commands and results', 'Comandos y resultados')}

| # | {T('Command', 'Comando')} | exit | {T('seconds', 'segundos')} |
|---|---|---|---|
{rows}

| {T('Check', 'Comprobación')} | {T('Result', 'Resultado')} |
|---|---|
| {T('Generator', 'Generador')} | {gen_line.split(' -> ')[0]} |
| {T('Notebook (fresh kernel)', 'Notebook (kernel nuevo)')} | {nb_line} |
| {T('Tests', 'Pruebas')} | **{passed} passed, {failed} failed** |
| {T('Logic checks', 'Comprobaciones lógicas')} | {metrics['logic_checks']['count']} · {T('violations', 'violaciones')} {metrics['logic_checks']['violations']} |
| {T('Baseline metrics', 'Métricas de la línea base')} | {len(metrics['metrics'])} {T('metrics, each recomputed independently from the CSV files by', 'métricas, cada una recalculada de forma independiente a partir de los CSV por')} `tests/test_baseline.py` |
| {T('Reproducibility check', 'Comprobación de reproducibilidad')} | {check_result[lang] if check_result else T('not run in this mode (use --check)', 'no ejecutada en este modo (usar --check)')} |

## {T('Input hashes (SHA-256)', 'Hashes de entrada (SHA-256)')}

| {T('File', 'Archivo')} | SHA-256 |
|---|---|
{hrows}

{T('Every other repository file is listed in', 'El resto de archivos del repositorio figura en')} `baseline/MANIFEST.sha256`.

## {T('Post-interview follow-up audit', 'Auditoría del seguimiento postentrevista')}

| {T('Item', 'Elemento')} | {T('Value', 'Valor')} |
|---|---|
| {T('Eligible leads with a held interview', 'Leads elegibles con entrevista realizada')} | {num(a['held'])} |
| {T('Excluded: 48-hour window not complete at the snapshot', 'Excluidos: ventana de 48 h no completa en el corte')} | {num(a['excluded_open_window'])} |
| {T('Denominator', 'Denominador')} | {num(a['denominator'])} |
| {T('Numerator (≥1 manual advisor call/WhatsApp with held < activity_at ≤ held + 48 h)', 'Numerador (≥1 llamada/WhatsApp manual del asesor con held < activity_at ≤ held + 48 h)')} | {num(a['numerator'])} |
| {T('Indicator', 'Indicador')} | **{pct(a['rate'])}** |
| {T('Advisor activities of these leads: in window / at the interview instant / before / after 48 h', 'Actividades del asesor de esos leads: en ventana / en el instante de la entrevista / antes / después de 48 h')} | {num(a['in_window'])} / {num(a['at_interview'])} / {num(a['before'])} / {num(a['after_48h'])} |
| {T("Contrast: wrong rule 'first activity of the lead within 48 h'", "Contraste: regla incorrecta 'primera actividad del lead en 48 h'")} | {num(a['wrong_rule'])} {T('leads (not used)', 'leads (no se usa)')} |
"""
        (BASE / ("F0_REPORT.es.md" if es else "F0_REPORT.md")).write_text(text, encoding="utf-8")


def main():
    # Guard (added in F1): this tool rebuilds baseline/ and must only run on the frozen v1.0.0-f0 tree.
    if (ROOT / "src" / "metrics.py").exists():
        raise SystemExit("f0_baseline.py only runs on the F0 tree (v1.0.0-f0); this tree is F1 or later and baseline/ is frozen.\n"
                         "Verify F0 from admissions-crm-analytics-v1.0.0-f0.zip in a clean folder; verify F1 with scripts/f1_run.py.")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare the clean run with the stored manifest")
    args = ap.parse_args()
    BASE.mkdir(exist_ok=True)
    stored = (BASE / "MANIFEST.sha256").read_text() if (BASE / "MANIFEST.sha256").exists() else None
    if args.check and stored is None:
        raise SystemExit("no stored baseline/MANIFEST.sha256 to check against")

    log = []
    clean(log)
    run("generate", [sys.executable, "src/generate_data.py"], log)
    run("notebook", [sys.executable, "scripts/build_notebook.py"], log)
    run("tests", [sys.executable, "-m", "pytest", "-q"], log)
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)

    env = environment()
    (BASE / "environment.txt").write_text(env, encoding="utf-8")
    text, tree_id = manifest()
    check_result = None
    if args.check:
        old = dict(reversed(l.split("  ", 1)) for l in stored.strip().splitlines())
        new = dict(reversed(l.split("  ", 1)) for l in text.strip().splitlines())
        diff = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        check_result = ({"en": f"identical to the stored manifest ({len(new)} files) — tree id {tree_id[:16]}",
                         "es": f"idéntica al manifiesto guardado ({len(new)} archivos) — tree id {tree_id[:16]}"}
                        if not diff else {"en": "DRIFT in: " + ", ".join(diff), "es": "DIFERENCIAS en: " + ", ".join(diff)})
        print("[check]", check_result["en"])
    else:
        (BASE / "MANIFEST.sha256").write_text(text, encoding="utf-8")
    metrics = json.loads((BASE / "metrics_v1.json").read_text(encoding="utf-8"))
    write_reports(log, tree_id, env, followup_audit(), metrics, check_result)
    for d in ROOT.rglob("__pycache__"):
        shutil.rmtree(d)
    print(f"baseline {BASELINE_ID} · tree id {tree_id}")
    if check_result and check_result["en"].startswith("DRIFT"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
