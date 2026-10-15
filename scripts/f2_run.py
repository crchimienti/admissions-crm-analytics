"""F2 clean run (v1.2.3-f2): canonical schema crm-canonical/0.1.1, comparison with the frozen F0 and F1 references and
with the previous F2 revision (v1.2.2-f2).

Ejecución limpia de F2 (v1.2.3-f2): esquema canónico, comparación con F0 y F1 congelados y con la revisión F2 anterior.

Steps (real subprocesses; exit codes and durations are recorded):
  0. environment  compare installed versions with baseline/environment.txt
  1. frozen       hash baseline/ (F0), reports/f1/ (F1) and the stored v1.2.0-f2 / v1.2.1-f2 / v1.2.2-f2 manifests against their ids
  2. clean        remove data/, the executed notebook, build/, caches and the generated files of reports/f2/
                  (never baseline/, reports/f1/ or the stored previous F2 manifests)
  3. generate     python src/generate_data.py; CSV hashes must equal the F0 manifest
  4. notebook     python scripts/build_notebook.py; the executed notebook must equal the F1 manifest
  5. map          python scripts/map_to_canonical.py -> build/canonical/admissions/ (outside the tree manifest)
  6. tests        python -m pytest -q (no xfail allowed)
  7. compare      classify every file against the F1 manifest and against the v1.2.2-f2 manifest; only declared
                  modifications and new files are accepted (src/metrics.py: authorised v1.2.1-f2 fix)
  8. reconcile    47 metrics, direct route (src/metrics.py) and canonical route, vs F0 and F1; the direct route must
                  rewrite reports/f1/metrics_f1.json byte for byte; hand fixture: five variants through the full path
  9. frozen again baseline/, reports/f1/ and the previous F2 manifests byte-identical before and after the run
 10. outputs      reports/f2/: metrics_f2_canonical.json, handcalc_variants.json, canonical_admissions.sha256,
                  MANIFEST_F2.sha256, F2_REPORT(.es).md, F1_COMPARISON(.es).md, F2_PREV_COMPARISON(.es).md

Usage:
  python scripts/f2_run.py          # create / refresh the v1.2.3-f2 manifest and reports
  python scripts/f2_run.py --check  # same clean run, then require the stored F2 manifest (exit 1 on drift)
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
OUT = ROOT / "reports" / "f2"
VERSION_ID = "v1.2.3-f2"
F0_ID, F1_ID, PREV_ID = "v1.0.0-f0", "v1.1.0-f1", "v1.2.2-f2"
F0_TREE_ID = "eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df"
F1_TREE_ID = "9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651"
PREV_TREE_ID = "ddfc93cf87313a3b22d4a59961d938c420fcd97d15c8b530b0947457d9afc1a9"
PREV_MANIFEST = "reports/f2/MANIFEST_F2_v1.2.2.sha256"
V121_TREE_ID = "f71ca2471525fbaa28b3b2a29f1012f5c9a18671a2f57c178de97a15788a95e4"
V121_MANIFEST = "reports/f2/MANIFEST_F2_v1.2.1.sha256"
V120_TREE_ID = "2ba1a33f9001b613ed75192eee11c6c7c591c3cb321e51c07cb995b375eddc1e"
V120_MANIFEST = "reports/f2/MANIFEST_F2_v1.2.0.sha256"
KEPT_MANIFESTS = {PREV_MANIFEST: PREV_TREE_ID, V121_MANIFEST: V121_TREE_ID, V120_MANIFEST: V120_TREE_ID}
F0_FROZEN_OUTSIDE_MANIFEST = {
    "baseline/F0_REPORT.md": "573dc315e20b5cbbc1268952209b06eb1ef549fcf200f95ac38920ba4156c84f",
    "baseline/F0_REPORT.es.md": "418a2a5a2cd59e031493ae64f31a5da40193af18c35f9e44e9daf10a8939daec",
}
F1_REPORTS = {
    "reports/f1/MANIFEST_F1.sha256": F1_TREE_ID,
    "reports/f1/metrics_f1.json": "4538857acc710a84880e2cfdd72bbe43bfbe1d1cfda27130c73253ca83210959",
    "reports/f1/F1_REPORT.md": "a10de2fd7d97880a5a93def4a17c437d749579a85c75abbfae12041ea878f969",
    "reports/f1/F1_REPORT.es.md": "205afee143064287641b0d12b548d0fc179caae2f5028103bffac60f4dff8fe3",
    "reports/f1/F0_COMPARISON.md": "5ed91a354b773248af040e6214179733207a15f0d36950397946c7f1d6f5251c",
    "reports/f1/F0_COMPARISON.es.md": "18657f11ef901ef05b77452e5c0a8b13883d1664b8758eca8657ad6f047fd79d",
}
# --- against the F1 manifest ------------------------------------------------ #
DECLARED_MODIFIED = {
    "README.md": "F2 section, repository structure and how to run (no figure changed)",
    "README.es.md": "sección F2, estructura y cómo ejecutar (ninguna cifra cambia)",
    "scripts/f1_run.py": "guard only: refuses to run on the F2 tree (reports/f1/ is frozen)",
    "scripts/export_metrics.py": "guard only: refuses to write reports/f1/ on the F2 tree",
    "src/metrics.py": "authorised v1.2.1-f2 robustness fix (zero denominators, empty appointment structures); same 47 values",
}
DECLARED_NEW = {
    "schema/canonical_v0.1.yaml", "schema/canonical_v0.1.1.yaml", "docs/canonical_schema.md", "docs/canonical_schema.es.md",
    "docs/PROJECT_STATUS.md", "docs/PROJECT_STATUS.es.md", "tests/test_canonical_event_order.py", V120_MANIFEST, V121_MANIFEST,
    "src/canonical/__init__.py", "src/canonical/contract.py", "src/canonical/validate.py", "src/canonical/mapping.py",
    "src/canonical/history.py", "src/canonical/availability.py", "src/canonical/adapters/__init__.py",
    "src/canonical/adapters/admissions.py",
    "profiles/admissions/mapping_csv_v1.yaml", "profiles/admissions/kpi_requirements.yaml", "profiles/admissions/rules.yaml",
    "scripts/map_to_canonical.py", "scripts/f2_run.py",
    "tests/test_canonical_contract.py", "tests/test_canonical_mapping.py", "tests/test_canonical_timestamps.py",
    "tests/test_canonical_mapping_errors.py", "tests/test_canonical_availability.py", "tests/test_canonical_handcalc.py",
    "tests/test_regression_f1.py", "tests/test_metrics_robustness.py",
    "reports/f2/metrics_f2_canonical.json", "reports/f2/handcalc_variants.json", "reports/f2/canonical_admissions.sha256",
    PREV_MANIFEST,
}
DECLARED_NEW_DIRS = ("tests/fixtures/canonical_handcalc/", "tests/fixtures/mapping_errors/", "tests/fixtures/timezones/")
# --- against the previous F2 revision (v1.2.2-f2): documentation only -------- #
PREV_MODIFIED = {
    "docs/PROJECT_STATUS.md": "current restrictions vs future goals; UTC adapter and real-data / CRM readiness stated as not available",
    "docs/PROJECT_STATUS.es.md": "restricciones vigentes frente a objetivos futuros; adaptador UTC y preparación para datos reales / CRM indicados como no disponibles",
    "scripts/f2_run.py": "report template only: obsolete contract paragraph removed; v1.2.3-f2 identifiers",
    "reports/f2/metrics_f2_canonical.json": "only the version_id field (v1.2.2-f2 -> v1.2.3-f2); all values identical",
}
PREV_NEW = {PREV_MANIFEST}
REPORT_FILES = {"reports/f2/MANIFEST_F2.sha256", "reports/f2/F2_REPORT.md", "reports/f2/F2_REPORT.es.md",
                "reports/f2/F1_COMPARISON.md", "reports/f2/F1_COMPARISON.es.md",
                "reports/f2/F2_PREV_COMPARISON.md", "reports/f2/F2_PREV_COMPARISON.es.md"}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".git", "build"}
PKGS = ["numpy", "pandas", "pyyaml", "matplotlib", "nbformat", "nbconvert", "ipykernel", "pytest"]
VARIANTS = ["v_full", "v_milestone", "v_snapshot", "v_no_automated", "v_no_appointments"]
FIXTURE = ROOT / "tests" / "fixtures" / "canonical_handcalc"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not any(part in EXCLUDE_DIRS for part in rel.parts):
            yield rel.as_posix(), p


def manifest(path: Path):
    return manifest_text(path.read_text())


def manifest_text(text):
    return {p: h for h, p in (l.split("  ", 1) for l in text.strip().splitlines())}


def frozen_hashes():
    return {rel: sha(p) for rel, p in tree_files() if rel.startswith(("baseline/", "reports/f1/")) or rel in KEPT_MANIFESTS}


def frozen_problems(h):
    probs = []
    if h.get("baseline/MANIFEST.sha256") != F0_TREE_ID:
        probs.append("baseline/MANIFEST.sha256 is not the F0 tree id")
    for rel, tid in KEPT_MANIFESTS.items():
        if h.get(rel) != tid:
            probs.append(f"{rel} is not its tree id")
    man = manifest(ROOT / "baseline" / "MANIFEST.sha256")
    for rel, ref in {**{k: v for k, v in man.items() if k.startswith("baseline/")}, **F0_FROZEN_OUTSIDE_MANIFEST, **F1_REPORTS}.items():
        if h.get(rel) != ref:
            probs.append(f"{rel} differs from its frozen hash")
    extra = set(h) - set(man) - set(F0_FROZEN_OUTSIDE_MANIFEST) - set(F1_REPORTS) - {"baseline/MANIFEST.sha256"} - set(KEPT_MANIFESTS)
    probs += [f"unexpected file {r}" for r in sorted(extra)]
    return probs


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
    return found, {k: (recorded.get(k), v) for k, v in found.items() if recorded.get(k) != v}


def clean(log):
    t0, removed = time.time(), []
    for rel in ("data", "notebooks/admissions_analysis.ipynb", "build", ".pytest_cache"):
        p = ROOT / rel
        if p.is_dir():
            shutil.rmtree(p); removed.append(rel + "/")
        elif p.exists():
            p.unlink(); removed.append(rel)
    if OUT.exists():
        for p in OUT.iterdir():
            if p.relative_to(ROOT).as_posix() not in KEPT_MANIFESTS:
                p.unlink(); removed.append(p.relative_to(ROOT).as_posix())
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    log.append({"step": "clean", "cmd": "remove data/, notebook, build/, caches, generated reports/f2 files", "exit": 0,
                "secs": round(time.time() - t0, 1), "out": ", ".join(removed)})
    print("[clean] removed:", ", ".join(removed))


def classify(ref_manifest, modified, new, new_dirs=(), skip=()):
    now = {rel: sha(p) for rel, p in tree_files()}
    rows, problems = [], []
    for rel in sorted(set(ref_manifest) | set(now)):
        if rel in REPORT_FILES or rel in skip:
            continue
        ref, cur = ref_manifest.get(rel), now.get(rel)
        if ref and cur == ref:
            status = "unchanged"
        elif ref and cur is None:
            status = "REMOVED"; problems.append(rel)
        elif ref and rel in modified:
            status = "modified (declared)"
        elif ref:
            status = "MODIFIED (undeclared)"; problems.append(rel)
        elif rel in new or rel.startswith(tuple(new_dirs)):
            status = "new (declared)"
        else:
            status = "NEW (undeclared)"; problems.append(rel)
        rows.append({"file": rel, "status": status, "ref": ref, "cur": cur})
    return rows, problems


def reconcile_and_variants():
    sys.path.insert(0, str(ROOT / "src"))
    import metrics
    from canonical import mapping, availability
    from canonical.adapters import admissions as ad
    from canonical.validate import validate
    f0 = json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8"))
    f1_text = (ROOT / "reports" / "f1" / "metrics_f1.json").read_text(encoding="utf-8")
    f1 = json.loads(f1_text)
    # direct route: src/metrics.py on the CSV files, exactly as F1 did
    direct_doc = metrics.baseline_document(metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml"), F1_ID, ROOT)
    direct_identical = json.dumps(direct_doc, indent=2, ensure_ascii=False) + "\n" == f1_text
    rec_direct = metrics.reconcile(direct_doc, f0)
    # canonical route
    can = validate(mapping.map_directory(ROOT / "data"))
    ad.check_profile(can)
    ev = ad.evaluate(can)
    strip = lambda e: {k: v for k, v in e.items() if k != "status"}
    doc = {"metrics": [strip(e) for e in ev["baseline_metrics"]]}
    rec0, rec1 = metrics.reconcile(doc, f0), metrics.reconcile(doc, f1)
    metrics_doc = {
        "schema_version": "1.0", "version_id": VERSION_ID,
        "route": "CSV -> canonical dataset (crm-canonical/0.1, validated by contract 0.1.1) -> adapters/admissions -> src/metrics.py (F1 + authorised v1.2.1-f2 fix)",
        "note": metrics.SYNTHETIC_NOTE, "capabilities": ev["capabilities"],
        "baseline_metrics": ev["baseline_metrics"], "catalogue": ev["catalogue"]}
    exp = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
    ref = {**exp["metrics_all_eligible"], **exp["metrics_mature_eligible"], **exp["history_full_event_history"]}
    r6 = lambda v: {k: r6(x) for k, x in v.items()} if isinstance(v, dict) else (round(v, 6) if isinstance(v, float) else v)
    variants = {}
    for name in VARIANTS:
        c = ad.load(FIXTURE / name)
        st = ad.catalogue_availability(c)
        e = exp["variants"][name]
        av = [s["id"] for s in st if s["status"] == "available"]
        na = [{"id": s["id"], "reason": s["reason"]} for s in st if s["status"] == "not_available"]
        ids = av + [x["id"] for x in na]
        out = ad.evaluate(c)
        availability.check_no_leak(out["catalogue"] + out["baseline_metrics"])
        cat = {x["id"]: x for x in out["catalogue"]}
        full_path_status_ok = all(cat[i]["status"] == "available" for i in e["available"]) and \
            all(cat[x["id"]]["status"] == "not_available" and cat[x["id"]]["reason"] == x["reason"] for x in e["not_available"])
        mism = []
        checked = [i for i in e["available"] if i not in e["capabilities_without_expected_value"]]
        for i in checked:
            got = {f: cat[i].get(f) for f in ("value", "numerator", "denominator") if f in ref[i]}
            if r6(got) != r6({f: ref[i][f] for f in got}):
                mism.append(i)
        variants[name] = {
            "history_mode": c.dataset["history_mode"], "available": len(av), "not_available": len(na),
            "ids_once": len(ids) == len(set(ids)) == 31,
            "matrix_matches_expected": sorted(av) == sorted(e["available"]) and
            sorted(na, key=lambda x: x["id"]) == sorted(e["not_available"], key=lambda x: x["id"]),
            "full_path_status_matches": full_path_status_ok, "values_checked": len(checked), "value_mismatches": mism,
            "computed_reasons_in_baseline_metrics": sorted({x["reason"] for x in out["baseline_metrics"]
                                                            if x["status"] == "not_available" and x["reason"] in ("DEN0", "INSUF")}),
            "catalogue": out["catalogue"]}
    return {"direct_identical": direct_identical, "rec_direct": rec_direct, "rec0": rec0, "rec1": rec1,
            "metrics_doc": metrics_doc, "variants": variants, "expected": exp}


def f2_manifest():
    lines = [f"{sha(p)}  {rel}" for rel, p in tree_files() if rel not in REPORT_FILES]
    text = "\n".join(lines) + "\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def parse_pytest(out):
    g = lambda k: int(m.group(1)) if (m := re.search(rf"(\d+) {k}", out)) else 0
    return g("passed"), g("failed"), g("xfailed"), g("xpassed")


def _fmt(v):
    return "—" if v is None else v


def write_reports(log, env, env_diffs, rows1, rows0, R, canon_lines, tree_id, check_result, fz_before, fz_after, fz_probs):
    when = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    passed, failed, xfailed, xpassed = parse_pytest(next(s["out"] for s in log if s["step"] == "tests"))
    rec0, rec1, recd, variants, exp = R["rec0"], R["rec1"], R["rec_direct"], R["variants"], R["expected"]
    m0, m1, md_ = (int(r.match.astype(bool).sum()) for r in (rec0, rec1, recd))
    counts = lambda rows: ", ".join(f"{k}: {v}" for k, v in sorted({r["status"]: sum(x["status"] == r["status"] for x in rows) for r in rows}.items()))
    for lang in ("en", "es"):
        es = lang == "es"
        T = (lambda e, s: s) if es else (lambda e, s: e)
        sfx = ".es" if es else ""
        steps = "\n".join(f"| {i + 1} | `{s['cmd']}` | {s['exit']} | {s['secs']} |" for i, s in enumerate(log))
        envtxt = ", ".join(f"{k}=={v}" for k, v in env.items())
        envchk = (T("identical to baseline/environment.txt", "idéntico a baseline/environment.txt") if not env_diffs else
                  T("DIFFERENT from baseline/environment.txt: ", "DISTINTO de baseline/environment.txt: ") + str(env_diffs))
        chk = check_result[lang] if check_result else T("not run in this mode (use --check)", "no ejecutada en este modo (usar --check)")
        frozen_line = (T("byte-identical before and after; frozen ids verified", "idénticos byte a byte antes y después; ids congelados verificados")
                       if fz_before == fz_after and not fz_probs else T("PROBLEM: ", "PROBLEMA: ") + "; ".join(fz_probs or ["changed during the run"]))
        vrows = "\n".join(
            f"| `{n}` | {v['history_mode']} | {v['available']} + {v['not_available']} | {'✓' if v['ids_once'] else '✗'} | "
            f"{'✓' if v['matrix_matches_expected'] and v['full_path_status_matches'] else '✗'} | "
            f"{v['values_checked'] - len(v['value_mismatches'])} / {v['values_checked']} | "
            f"{', '.join(v['computed_reasons_in_baseline_metrics']) or '—'} |" for n, v in variants.items())
        cov = "\n".join(f"| {k} | {'; '.join(v)} |" for k, v in exp["coverage"].items())
        canon = "\n".join(f"| `{l.split('  ')[1]}` | {l.split('(')[-1].split()[0]} | `{l.split()[0][:16]}` |" for l in canon_lines)
        mod1 = "\n".join(f"- `{r['file']}` — {DECLARED_MODIFIED[r['file']]}" for r in rows1 if r["status"] == "modified (declared)")
        mod0 = "\n".join(f"- `{r['file']}` — {PREV_MODIFIED.get(r['file'], '')}" for r in rows0 if r["status"] == "modified (declared)")
        new0 = "\n".join(f"- `{r['file']}`" for r in rows0 if r["status"] == "new (declared)")
        report = f"""{T('**Language:** English | [Español](F2_REPORT.es.md)', '**Idioma:** [English](F2_REPORT.md) | Español')}

# {T('F2 — run report', 'F2 — informe de ejecución')} (`{VERSION_ID}`)

{T('Generated by', 'Generado por')} `python scripts/f2_run.py{' --check' if check_result else ''}` · {when}.
{T('All data and figures are synthetic (seed 42 and a hand-built fixture). Scope: admissions profile only; no portability claim; no CRM connection.',
   'Todos los datos y cifras son sintéticos (semilla 42 y un fixture construido a mano). Alcance: solo el perfil de admisiones; sin afirmaciones de portabilidad; sin conexión a ningún CRM.')}

{T('**F2 close (documentation correction).** This delivery corrects only documentation of v1.2.2-f2 (approved as the F2 working version): the report no longer carries the obsolete paragraph on the contract, and PROJECT_STATUS separates current restrictions from future goals. Calculations, fixtures, data and the contract (crm-canonical/0.1.1) are unchanged. It replaces', '**Cierre de F2 (corrección de documentación).** Esta entrega corrige solo documentación de v1.2.2-f2 (aprobada como versión de trabajo de F2): el informe ya no contiene el párrafo obsoleto sobre el contrato y PROJECT_STATUS separa las restricciones vigentes de los objetivos futuros. Cálculos, fixtures, datos y contrato (crm-canonical/0.1.1) no cambian. Sustituye a')} `{PREV_ID}` ({T('tree id', 'tree id')} `{PREV_TREE_ID[:16]}…`, {T('manifest kept in', 'manifiesto conservado en')} `{PREV_MANIFEST}`).

## {T('Version', 'Versión')}

| {T('Item', 'Elemento')} | {T('Value', 'Valor')} |
|---|---|
| {T('F2 id', 'Identificador F2')} | `{VERSION_ID}` |
| {T('F2 tree id (SHA-256 of', 'Tree id F2 (SHA-256 de')} `reports/f2/MANIFEST_F2.sha256`) | `{tree_id}` |
| {T('References', 'Referencias')} | `{F0_ID}` `{F0_TREE_ID[:16]}…` · `{F1_ID}` `{F1_TREE_ID[:16]}…` · `v1.2.0-f2` `{V120_TREE_ID[:16]}…` · `v1.2.1-f2` `{V121_TREE_ID[:16]}…` · `{PREV_ID}` `{PREV_TREE_ID[:16]}…` |
| {T('Canonical contract', 'Contrato canónico')} | `crm-canonical/0.1.1` (`schema/canonical_v0.1.1.yaml`; {T('additive revision of 0.1: optional stage_events.seq and rules C08-C09', 'revisión aditiva de 0.1: stage_events.seq opcional y reglas C08-C09')}) |
| Git | {T('no commit or tag (not a git repository; not authorised)', 'sin commit ni tag (no es un repositorio git; no autorizado)')} |
| {T('Environment', 'Entorno')} | {envtxt} — {envchk} |

## {T('Commands and results', 'Comandos y resultados')}

| # | {T('Command', 'Comando')} | exit | {T('seconds', 'segundos')} |
|---|---|---|---|
{steps}

| {T('Check', 'Comprobación')} | {T('Result', 'Resultado')} |
|---|---|
| {T('Tests', 'Pruebas')} | **{passed} passed, {failed} failed, {xfailed} xfailed, {xpassed} xpassed** |
| {T('Direct route: F1 metrics document generated in memory by src/metrics.py, compared with reports/f1/metrics_f1.json (which is never written)', 'Ruta directa: documento de métricas de F1 generado en memoria por src/metrics.py y comparado con reports/f1/metrics_f1.json (que nunca se escribe)')} | {T('byte-identical', 'idéntico byte a byte') if R['direct_identical'] else T('DIFFERENT', 'DISTINTO')} |
| {T('47 metrics, direct route vs F0', '47 métricas, ruta directa frente a F0')} | **{md_} / {len(recd)}** |
| {T('47 metrics, canonical route vs F0 / vs F1', '47 métricas, ruta canónica frente a F0 / F1')} | **{m0} / {len(rec0)}** · **{m1} / {len(rec1)}** {T('(ids, order, descriptive fields, numerators, denominators, values at 6 decimals)', '(ids, orden, campos descriptivos, numeradores, denominadores, valores a 6 decimales)')} |
| {T('Frozen: baseline/ (F0), reports/f1/ (F1), v1.2.0-f2, v1.2.1-f2 and v1.2.2-f2 manifests', 'Congelados: baseline/ (F0), reports/f1/ (F1), manifiestos v1.2.0-f2, v1.2.1-f2 y v1.2.2-f2')} | {frozen_line} ({len(fz_after)} {T('files', 'archivos')}) |
| {T('Reproducibility', 'Reproducibilidad')} | {chk} |

{T('Value by value, the 47 metrics before (F0, F1) and after (this revision, both routes) are listed in', 'Valor a valor, las 47 métricas antes (F0, F1) y después (esta revisión, ambas rutas) están en')} [`F1_COMPARISON{sfx}.md`](F1_COMPARISON{sfx}.md).

## {T('Event order and contract (v1.2.2-f2)', 'Orden de eventos y contrato (v1.2.2-f2)')}

{T('The approved stage_events specification (key record_id + seq; required record_id, seq, stage, entered_at, event_kind; optional exited_at, changed_by_type; seq orders equal timestamps) is mapped column by column in docs/canonical_schema.md §11.3. The contract becomes crm-canonical/0.1.1, an additive revision: an optional seq keeps the source order and is unique per record and consistent with occurred_at (C08). Without seq, events of one record with the same occurred_at have an indeterminate order (C09); it is never resolved by stage, event_id or file position (the event_id tie-break that v1.2.1-f2 used inside time_in_stage was removed). Only time_in_stage depends on order and is then not_available with reason ORD. Regressions, reopens, entry counts and first entries do not depend on order: tests/test_canonical_event_order.py checks them with simultaneous events, shuffled rows and renamed ids. exited_at and changed_by_type are not represented (§11.3). The admissions CSV gives no order, so its mapping still emits crm-canonical/0.1 datasets without seq, which 0.1.1 accepts.',
   'La especificación aprobada de stage_events (clave record_id + seq; obligatorios record_id, seq, stage, entered_at, event_kind; opcionales exited_at, changed_by_type; seq ordena los timestamps iguales) se mapea columna a columna en docs/canonical_schema.es.md §11.3. El contrato pasa a crm-canonical/0.1.1, una revisión aditiva: un seq opcional conserva el orden de la fuente y es único por registro y coherente con occurred_at (C08). Sin seq, los eventos de un registro con el mismo occurred_at tienen un orden indeterminado (C09); nunca se resuelve por etapa, event_id ni posición en el archivo (se ha eliminado el desempate por event_id que v1.2.1-f2 usaba dentro de time_in_stage). Solo time_in_stage depende del orden y entonces es not_available con motivo ORD. Retrocesos, reaperturas, conteos de entradas y primeras entradas no dependen del orden: tests/test_canonical_event_order.py lo comprueba con eventos simultáneos, filas barajadas e ids renombrados. exited_at y changed_by_type no se representan (§11.3). El CSV de admisiones no da ningún orden, así que su mapeo sigue emitiendo datasets crm-canonical/0.1 sin seq, que 0.1.1 acepta.')}

{T('current_status is not the approved status = open/won/lost: it keeps the profile operational statuses (new, working, iloc_sequence, nurture, closed_won, closed_lost). The outcome is derived from current_stage only (closed_won → won, closed_lost → lost, else open), so a nurture record is lost, never a fourth outcome; checked on the fixture and on the generated data (docs §11.2).',
   'current_status no es el status = open/won/lost aprobado: conserva los estados operativos del perfil (new, working, iloc_sequence, nurture, closed_won, closed_lost). El resultado se deriva solo de current_stage (closed_won → ganado, closed_lost → perdido, el resto → abierto), así que un registro en nurture está perdido y nunca es un cuarto resultado; comprobado en el fixture y en los datos generados (docs §11.2).')}

## {T('Robustness defects fixed in src/metrics.py (authorised, v1.2.1-f2)', 'Defectos de robustez corregidos en src/metrics.py (autorizado, v1.2.1-f2)')}

| {T('Defect in v1.2.0-f2', 'Defecto en v1.2.0-f2')} | {T('Input that triggered it', 'Entrada que lo provocaba')} | {T('Fix', 'Corrección')} |
|---|---|---|
| MP1 `ZeroDivisionError` `forms_over_interviews_held`; {T('possible inf in other ratios', 'posible inf en otras razones')} | {T('no mature lead with a held interview', 'ningún lead maduro con entrevista realizada')} | {T('every ratio of baseline_metrics and directional_rates through rate() → NaN → DEN0', 'todas las razones de baseline_metrics y directional_rates por rate() → NaN → DEN0')} |
| MP3 `TypeError` `Context.bot_pre` | {T('no appointment row', 'ninguna fila de citas')} | {T('slot lookup with reindex (datetime kept)', 'búsqueda de la franja con reindex (se conserva el tipo fecha)')} |
| MP3b `TypeError` `show_rate_per_lead` | {T('no appointment row', 'ninguna fila de citas')} | {T('Context.showlead typed bool', 'Context.showlead con tipo bool')} |
| MP4 `AttributeError` `Context.personal_wa_appointments` | {T('no held / no-show appointment from 2025-07-01', 'ninguna cita realizada / no-show desde el 2025-07-01')} | {T('typed boolean column', 'columna booleana tipada')} |

{T('No definition changed. The adapter now separates three cases and never turns them into zero: module absent (HM, HF, AUT, APT, decided first), zero denominator (DEN0) and insufficient data (INSUF). Tested in tests/test_metrics_robustness.py, including a dataset without appointments from 2025-07-01 and one without any appointment.',
   'No cambia ninguna definición. El adaptador separa ahora tres casos y nunca los convierte en cero: módulo ausente (HM, HF, AUT, APT, se decide primero), denominador cero (DEN0) y datos insuficientes (INSUF). Probado en tests/test_metrics_robustness.py, incluido un dataset sin citas desde el 2025-07-01 y otro sin ninguna cita.')}

## {T('Hand-calculated fixture: five variants through the full path', 'Fixture calculado a mano: cinco variantes por la ruta completa')}

| {T('Variant', 'Variante')} | history_mode | available + not_available | {T('31 ids once', '31 ids una vez')} | {T('matrix = expected', 'matriz = esperada')} | {T('values via src/metrics.py = hand values', 'valores por src/metrics.py = a mano')} | {T('DEN0 / INSUF outside the catalogue', 'DEN0 / INSUF fuera del catálogo')} |
|---|---|---|---|---|---|---|
{vrows}

{T('Every available value of every variant is checked through canonical files → validation → profile rules → adapter → src/metrics.py (+ history.py); the independent recomputation in the tests reproduces the same values. The DEN0 rates outside the catalogue are the nurture rates (the fixture has no nurture data) and, where present, a personal-WhatsApp rate with an empty group.',
   'Cada valor disponible de cada variante se comprueba por archivos canónicos → validación → reglas del perfil → adaptador → src/metrics.py (+ history.py); el recálculo independiente de las pruebas reproduce los mismos valores. Las tasas DEN0 fuera del catálogo son las de nurture (el fixture no tiene datos de nurture) y, cuando aparece, una tasa de WhatsApp personalizado con un grupo vacío.')}

### {T('Fixture inventory and coverage', 'Inventario y cobertura del fixture')}

{T('The F2 fixture has **12 hand-built synthetic records** (10 eligible, 1 duplicate, 1 reactivation), 32 activities, 11 appointments and 27 full-history stage events (24 first-entry milestones in the milestone variant). It is independent of the generator; `tests/fixtures/canonical_handcalc/expected.json` holds the source tables, the derivations and every expected value, calculated by hand. **It replaces the earlier 9-record draft (R1–R9); it is not the previously approved fixture**, which could not be recovered from this session and was not reconstructed. Its provenance (dates and appointments changed in v1.2.0-f2, follow-up boundary activities added in v1.2.1-f2) is recorded in `expected.json`.',
   'El fixture de F2 tiene **12 registros sintéticos construidos a mano** (10 elegibles, 1 duplicado, 1 reactivación), 32 actividades, 11 citas y 27 eventos de etapa con historial completo (24 hitos de primera entrada en la variante de hitos). Es independiente del generador; `tests/fixtures/canonical_handcalc/expected.json` contiene las tablas de origen, las derivaciones y todos los valores esperados, calculados a mano. **Sustituye al borrador anterior de 9 registros (R1–R9); no es el fixture aprobado previamente**, que no pudo recuperarse de esta sesión y no se ha reconstruido. Su procedencia (fechas y citas cambiadas en v1.2.0-f2, actividades del límite de seguimiento añadidas en v1.2.1-f2) queda registrada en `expected.json`.')}

| {T('Case', 'Caso')} | {T('Rows', 'Filas')} |
|---|---|
{cov}

## {T('Canonical admissions dataset (build/canonical/admissions, outside the manifest)', 'Dataset canónico de admisiones (build/canonical/admissions, fuera del manifiesto)')}

| {T('File', 'Archivo')} | {T('rows', 'filas')} | SHA-256 |
|---|---|---|
{canon}

## {T('Files', 'Archivos')}

**{T('Against F1', 'Frente a F1')}** (`reports/f1/MANIFEST_F1.sha256`): {counts(rows1)}. {T('Modified F1 files:', 'Archivos de F1 modificados:')}

{mod1}

**{T('Against the previous F2 revision', 'Frente a la revisión F2 anterior')}** (`{PREV_ID}`, `{PREV_MANIFEST}`): {counts(rows0)}. {T('Modified:', 'Modificados:')}

{mod0}

{T('New:', 'Nuevos:')}

{new0}

{T('Per-file hashes:', 'Hashes por archivo:')} [`F1_COMPARISON{sfx}.md`](F1_COMPARISON{sfx}.md) · [`F2_PREV_COMPARISON{sfx}.md`](F2_PREV_COMPARISON{sfx}.md).
"""
        (OUT / f"F2_REPORT{sfx}.md").write_text(report, encoding="utf-8")

        def file_table(rows, labels, notes):
            return "\n".join(f"| `{r['file']}` | {r['status']} | `{(r['ref'] or '—')[:16]}` | `{(r['cur'] or '—')[:16]}` | "
                             f"{notes.get(r['file'], '') if r['status'].startswith('modified') else ''} |" for r in rows)
        mrow = "\n".join(
            f"| `{i}` | {_fmt(r.value_reference)} | {_fmt(rec1.loc[i, 'value_reference'])} | {_fmt(recd.loc[i, 'value'])} | {_fmt(r.value)} | "
            f"{_fmt(r.numerator)} / {_fmt(r.denominator)} | {'✓' if r.match else '✗'} | {'✓' if rec1.loc[i, 'match'] else '✗'} | {'✓' if recd.loc[i, 'match'] else '✗'} |"
            for i, r in rec0.iterrows())
        comp = f"""{T('**Language:** English | [Español](F1_COMPARISON.es.md)', '**Idioma:** [English](F1_COMPARISON.md) | Español')}

# {VERSION_ID} {T('vs F1 — files and the 47 metrics before and after', 'frente a F1 — archivos y las 47 métricas antes y después')}

{T('Reference', 'Referencia')}: `{F1_ID}` (`reports/f1/MANIFEST_F1.sha256`, tree id `{F1_TREE_ID}`). {T('Hashes truncated to 16 characters.', 'Hashes truncados a 16 caracteres.')}

## {T('47 metrics', '47 métricas')} — {T('canonical vs F0', 'canónica frente a F0')} {m0}/47 · {T('vs F1', 'frente a F1')} {m1}/47 · {T('direct vs F0', 'directa frente a F0')} {md_}/47

{T('Before: F0 (baseline/metrics_v1.json) and F1 (reports/f1/metrics_f1.json). After: this revision, direct route (src/metrics.py on the CSV files) and canonical route (CSV → canonical dataset, contract 0.1.1 → adapter → src/metrics.py). Values at the reference rounding of 6 decimals with no extra tolerance; numerators, denominators and descriptive fields must also be equal.',
   'Antes: F0 (baseline/metrics_v1.json) y F1 (reports/f1/metrics_f1.json). Después: esta revisión, ruta directa (src/metrics.py sobre los CSV) y ruta canónica (CSV → dataset canónico, contrato 0.1.1 → adaptador → src/metrics.py). Valores al redondeo de la referencia (6 decimales) sin tolerancia adicional; numeradores, denominadores y campos descriptivos también deben ser iguales.')}

| {T('Metric', 'Métrica')} | F0 | F1 | {T('after, direct', 'después, directa')} | {T('after, canonical', 'después, canónica')} | {T('num. / den. after', 'num. / den. después')} | {T('canonical = F0', 'canónica = F0')} | {T('canonical = F1', 'canónica = F1')} | {T('direct = F0', 'directa = F0')} |
|---|---|---|---|---|---|---|---|---|
{mrow}

## {T('Files', 'Archivos')}

| {T('File', 'Archivo')} | {T('Status', 'Estado')} | SHA-256 F1 | SHA-256 {VERSION_ID} | {T('Declared change', 'Cambio declarado')} |
|---|---|---|---|---|
{file_table(rows1, None, DECLARED_MODIFIED)}
"""
        (OUT / f"F1_COMPARISON{sfx}.md").write_text(comp, encoding="utf-8")
        comp0 = f"""{T('**Language:** English | [Español](F2_PREV_COMPARISON.es.md)', '**Idioma:** [English](F2_PREV_COMPARISON.md) | Español')}

# {VERSION_ID} {T('vs', 'frente a')} {PREV_ID}

{T('Reference', 'Referencia')}: `{PREV_MANIFEST}` (tree id `{PREV_TREE_ID}`). {T('Report files are outside both manifests.', 'Los archivos de informe están fuera de ambos manifiestos.')} {counts(rows0)}.

| {T('File', 'Archivo')} | {T('Status', 'Estado')} | SHA-256 {PREV_ID} | SHA-256 {VERSION_ID} | {T('Declared change', 'Cambio declarado')} |
|---|---|---|---|---|
{file_table(rows0, None, PREV_MODIFIED)}
"""
        (OUT / f"F2_PREV_COMPARISON{sfx}.md").write_text(comp0, encoding="utf-8")


def main():
    # Guard (added in F3.0, v1.3.0-f3): this tool deletes and rewrites reports/f2/, which is frozen since F3.
    # It stops before touching any file; F2 (v1.2.3-f2) is verified from its ZIP in a clean folder.
    if (ROOT / "src" / "kpispec").exists():
        raise SystemExit("f2_run.py only runs on the F2 tree (v1.2.3-f2); this tree is F3 or later and reports/f2/ is frozen.\n"
                         "Verify F2 from admissions-crm-analytics-v1.2.3-f2.zip in a clean folder; verify F3 with scripts/f3_run.py.")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stored = (OUT / "MANIFEST_F2.sha256").read_text() if (OUT / "MANIFEST_F2.sha256").exists() else None
    if args.check and stored is None:
        raise SystemExit("no stored reports/f2/MANIFEST_F2.sha256 to check against")
    env, env_diffs = environment()
    print("[environment]", "matches baseline/environment.txt" if not env_diffs else f"DIFFERS: {env_diffs}")
    fz_before = frozen_hashes()
    probs = frozen_problems(fz_before)
    if probs:
        raise SystemExit("frozen references differ before the run: " + "; ".join(probs))
    print(f"[frozen] F0, F1 and the previous F2 manifests verified ({len(fz_before)} files)")

    log = []
    clean(log)
    run("generate", [sys.executable, "src/generate_data.py"], log)
    f0 = manifest(ROOT / "baseline" / "MANIFEST.sha256")
    bad = [p for p in ("data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv") if sha(ROOT / p) != f0[p]]
    if bad:
        raise SystemExit(f"generated data differ from F0: {bad}")
    run("notebook", [sys.executable, "scripts/build_notebook.py"], log)
    f1 = manifest(ROOT / "reports" / "f1" / "MANIFEST_F1.sha256")
    if sha(ROOT / "notebooks" / "admissions_analysis.ipynb") != f1["notebooks/admissions_analysis.ipynb"]:
        raise SystemExit("executed notebook differs from F1")
    canon_out = run("map", [sys.executable, "scripts/map_to_canonical.py"], log)
    tests_out = run("tests", [sys.executable, "-m", "pytest", "-q"], log)
    if parse_pytest(tests_out)[2] or parse_pytest(tests_out)[3]:
        raise SystemExit("xfail / xpass found: every test must pass normally")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)

    R = reconcile_and_variants()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "metrics_f2_canonical.json").write_text(json.dumps(R["metrics_doc"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "handcalc_variants.json").write_text(json.dumps(R["variants"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    canon_lines = [l for l in canon_out.splitlines() if "build/canonical" in l]
    (OUT / "canonical_admissions.sha256").write_text("\n".join(l.split("  (")[0] for l in canon_lines) + "\n", encoding="utf-8")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)

    rows1, prob1 = classify(f1, DECLARED_MODIFIED, DECLARED_NEW, DECLARED_NEW_DIRS, skip=set(F1_REPORTS))
    rows0, prob0 = classify(manifest(ROOT / PREV_MANIFEST), PREV_MODIFIED, PREV_NEW)
    fz_after = frozen_hashes()
    fz_probs = frozen_problems(fz_after)
    text, tree_id = f2_manifest()
    check_result = None
    if args.check:
        old, new = manifest_text(stored), manifest_text(text)
        diff = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        check_result = ({"en": f"identical to the stored F2 manifest ({len(new)} files) — tree id {tree_id[:16]}",
                         "es": f"idéntica al manifiesto F2 guardado ({len(new)} archivos) — tree id {tree_id[:16]}"}
                        if not diff else {"en": "DRIFT in: " + ", ".join(diff), "es": "DIFERENCIAS en: " + ", ".join(diff)})
        print("[check]", check_result["en"])
        (OUT / "MANIFEST_F2.sha256").write_text(stored, encoding="utf-8")
    else:
        (OUT / "MANIFEST_F2.sha256").write_text(text, encoding="utf-8")
    write_reports(log, env, env_diffs, rows1, rows0, R, canon_lines, tree_id, check_result, fz_before, fz_after, fz_probs)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    V = R["variants"]
    ok_variants = all(v["ids_once"] and v["matrix_matches_expected"] and v["full_path_status_matches"] and not v["value_mismatches"]
                      for v in V.values())
    ok_metrics = R["direct_identical"] and all(bool(r.match.astype(bool).all()) for r in (R["rec0"], R["rec1"], R["rec_direct"]))
    print(f"[compare] vs F1: {prob1 or 'no problems'} · vs {PREV_ID}: {prob0 or 'no problems'} · frozen unchanged: {fz_before == fz_after and not fz_probs}")
    print(f"[reconcile] direct = F1 document: {R['direct_identical']} · canonical F0 {int(R['rec0'].match.astype(bool).sum())}/47 · F1 {int(R['rec1'].match.astype(bool).sum())}/47")
    print("[variants] " + " · ".join(f"{k} {v['available']}+{v['not_available']} values {v['values_checked'] - len(v['value_mismatches'])}/{v['values_checked']}" for k, v in V.items()))
    print(f"F2 {VERSION_ID} · tree id {tree_id}")
    if (prob1 or prob0 or fz_before != fz_after or fz_probs or not ok_metrics or not ok_variants
            or (check_result and check_result["en"].startswith("DRIFT"))):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
