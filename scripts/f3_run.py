"""F3.0 clean run (v1.3.1-f3): declarative KPI engine in parallel with src/metrics.py, compared with the frozen F0, F1
and F2 references.

Ejecución limpia de F3.0: motor declarativo de KPIs en paralelo con src/metrics.py, comparado con F0, F1 y F2.

Steps (real subprocesses; exit codes and durations are recorded):
  0. environment  compare installed versions with baseline/environment.txt
  1. frozen       hash baseline/ (F0), reports/f1/ (F1) and reports/f2/ (F2, v1.2.3-f2) against their pinned hashes
  2. clean        remove data/, the executed notebook, build/, caches and the generated files of reports/f3/
                  (never baseline/, reports/f1/, reports/f2/ or reports/f3/MANIFEST_F3_v1.3.0.sha256)
  3. generate     python src/generate_data.py; CSV hashes must equal the F0 manifest
  4. notebook     python scripts/build_notebook.py; the executed notebook must equal the F1 manifest
  5. map          python scripts/map_to_canonical.py -> build/canonical/admissions/ (outside the tree manifest)
  6. tests        python -m pytest -q (no xfail / xpass allowed)
  7. compare      classify every file against reports/f2/MANIFEST_F2.sha256 and against the v1.3.0-f3 manifest
                  (reports/f3/MANIFEST_F3_v1.3.0.sha256, pinned): unchanged / modified (declared) / new (declared);
                  anything else fails
  8. reconcile    the eight engine KPIs vs F0, F1, F2 and src/metrics.py (in memory, no reference written); the 47
                  metrics of src/metrics.py vs F0 (direct and canonical routes); the five fixture variants
  9. frozen again baseline/, reports/f1/ and reports/f2/ byte-identical before and after the run
 10. outputs      reports/f3/: kpi_engine_results.json, kpi_handcalc_variants.json, MANIFEST_F3.sha256,
                  F3_REPORT(.es).md, F2_COMPARISON(.es).md

Usage:
  python scripts/f3_run.py          # create / refresh the F3 manifest and reports
  python scripts/f3_run.py --check  # same clean run, then require the stored F3 manifest (exit 1 on drift)
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
OUT = ROOT / "reports" / "f3"
VERSION_ID = "v1.3.1-f3"
F3_PREV_ID = "v1.3.0-f3"
F3_PREV_MANIFEST = "reports/f3/MANIFEST_F3_v1.3.0.sha256"
F3_PREV_TREE_ID = "b189d44e9d092d3481817a28e7fcca98535cf311286affa079bf5af1d560e1bd"
F0_ID, F1_ID, F2_ID = "v1.0.0-f0", "v1.1.0-f1", "v1.2.3-f2"
F0_TREE_ID = "eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df"
F1_TREE_ID = "9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651"
F2_TREE_ID = "a1df9fca9a38538f912fadfb437b4831f609962baa7b97fe763f68ec7a0885db"
FROZEN_OUTSIDE_F0_MANIFEST = {
    "baseline/MANIFEST.sha256": F0_TREE_ID,
    "baseline/F0_REPORT.md": "573dc315e20b5cbbc1268952209b06eb1ef549fcf200f95ac38920ba4156c84f",
    "baseline/F0_REPORT.es.md": "418a2a5a2cd59e031493ae64f31a5da40193af18c35f9e44e9daf10a8939daec",
    "reports/f1/MANIFEST_F1.sha256": F1_TREE_ID,
    "reports/f1/metrics_f1.json": "4538857acc710a84880e2cfdd72bbe43bfbe1d1cfda27130c73253ca83210959",
    "reports/f1/F1_REPORT.md": "a10de2fd7d97880a5a93def4a17c437d749579a85c75abbfae12041ea878f969",
    "reports/f1/F1_REPORT.es.md": "205afee143064287641b0d12b548d0fc179caae2f5028103bffac60f4dff8fe3",
    "reports/f1/F0_COMPARISON.md": "5ed91a354b773248af040e6214179733207a15f0d36950397946c7f1d6f5251c",
    "reports/f1/F0_COMPARISON.es.md": "18657f11ef901ef05b77452e5c0a8b13883d1664b8758eca8657ad6f047fd79d",
    "reports/f2/F1_COMPARISON.es.md": "44214c11fe2280d57b14ed870db7125a3262c943ee7d1f7c6e3f0310e667be85",
    "reports/f2/F1_COMPARISON.md": "16917d2fb745e74828942d7e82e17af91ca6b673d48ec8036ec6947acbfad416",
    "reports/f2/F2_PREV_COMPARISON.es.md": "2a3ffcb2235139487a853178b6405ff0dab6deecdadf2b92d9db86468c2337c1",
    "reports/f2/F2_PREV_COMPARISON.md": "bcc4260e96e1feb805d638c3536db4d1131ed1537816802e679d132955de6b2b",
    "reports/f2/F2_REPORT.es.md": "883c9941c063f4f5579341ddfa85067c32dc3a35cc53822fb24afb4d724b4d03",
    "reports/f2/F2_REPORT.md": "9669e60672845ddd6ffa71fcff1c74209e26eb5cfcf13d48cf20dfd2ce89af64",
    "reports/f2/MANIFEST_F2.sha256": F2_TREE_ID,
    "reports/f2/MANIFEST_F2_v1.2.0.sha256": "2ba1a33f9001b613ed75192eee11c6c7c591c3cb321e51c07cb995b375eddc1e",
    "reports/f2/MANIFEST_F2_v1.2.1.sha256": "f71ca2471525fbaa28b3b2a29f1012f5c9a18671a2f57c178de97a15788a95e4",
    "reports/f2/MANIFEST_F2_v1.2.2.sha256": "ddfc93cf87313a3b22d4a59961d938c420fcd97d15c8b530b0947457d9afc1a9",
    "reports/f2/canonical_admissions.sha256": "d9905805f678650b1e0db67300a44d6349c4f58623cfa21e65334aae5f722516",
    "reports/f2/handcalc_variants.json": "7eb2421b29e789e40cea77e6454fe9ea14f692fb06cb58baa3435050ad06e20c",
    "reports/f2/metrics_f2_canonical.json": "eaa32bdda075d587ff28cb4db6dcc17d0cd5246b66c17c41ea57db9b4079a29e",
}
DECLARED_MODIFIED = {
    "README.md": "F3.0 section, structure and how to run (no figure changed)",
    "README.es.md": "sección F3.0, estructura y cómo ejecutar (ninguna cifra cambia)",
    "docs/PROJECT_STATUS.md": "F3.0 state, F3.5 in the roadmap, FLD reason, frozen F2",
    "docs/PROJECT_STATUS.es.md": "estado de F3.0, F3.5 en la hoja de ruta, motivo FLD, F2 congelada",
    "scripts/f2_run.py": "guard only: refuses to run on the F3 tree before touching any file (reports/f2/ is frozen)",
    "src/canonical/adapters/admissions.py": "first_human_attempt extracted as a reusable profile function; metrics imported lazily (same results)",
}
# changes of v1.3.1-f3 against v1.3.0-f3 (corrections against the F3.0 approval spec)
DECLARED_MODIFIED_VS_F3_PREV = {
    "src/canonical/adapters/admissions.py": "src/metrics.py imported lazily, only by the metrics route (the engine no longer loads it, even indirectly); same results",
    "src/kpispec/fields.py": "stage fields with if_missing: HF need full history; via-appointment fields combine APT and FLD",
    "tests/test_kpi_engine_ops.py": "HF, FLD+HM and ORD tests",
    "tests/test_kpi_requirements.py": "eligibility equivalence on all five variants; missing field -> FLD or its capability reason; a null row is not FLD",
    "tests/test_kpi_handcalc.py": "runs in a fresh interpreter without loading src/metrics.py",
    "tests/test_kpi_isolation.py": "subprocess check: neither src/metrics.py nor the generator is loaded; no subprocess/os in src/kpispec",
    "tests/test_regression_f2.py": "declared change text of the adapter updated",
    "docs/kpi_spec.md": "version; no metrics import even indirectly; HF for stage fields",
    "docs/kpi_spec.es.md": "versión; sin importar metrics ni indirectamente; HF en campos de etapa",
    "docs/PROJECT_STATUS.md": "v1.3.1-f3 row; full F3.5 design, not yet authorised; eligibility on all variants",
    "docs/PROJECT_STATUS.es.md": "fila v1.3.1-f3; diseño completo de F3.5, todavía no autorizada; elegibilidad en todas las variantes",
    "README.md": "version heading", "README.es.md": "encabezado de versión",
    "scripts/f3_run.py": "v1.3.1-f3: keeps and pins the v1.3.0 manifest, classifies against it, lists intact files",
    "reports/f3/kpi_engine_results.json": "version_id and the route note (same results)",
}
DECLARED_NEW_VS_F3_PREV = {F3_PREV_MANIFEST}
DECLARED_NEW = {
    "schema/kpi_spec_v0.1.yaml", "profiles/admissions/kpis.yaml",
    "src/kpispec/__init__.py", "src/kpispec/spec.py", "src/kpispec/fields.py", "src/kpispec/engine.py",
    "docs/kpi_spec.md", "docs/kpi_spec.es.md", "scripts/f3_run.py",
    "tests/kpi_helpers.py", "tests/test_kpi_spec_schema.py", "tests/test_kpi_engine_ops.py", "tests/test_kpi_regression.py",
    "tests/test_kpi_handcalc.py", "tests/test_kpi_requirements.py", "tests/test_kpi_isolation.py",
    "tests/test_kpi_eligibility.py", "tests/test_regression_f2.py",
    "reports/f3/kpi_engine_results.json", "reports/f3/kpi_handcalc_variants.json", F3_PREV_MANIFEST,
}
REPORT_FILES = {"reports/f3/MANIFEST_F3.sha256", "reports/f3/F3_REPORT.md", "reports/f3/F3_REPORT.es.md",
                "reports/f3/F2_COMPARISON.md", "reports/f3/F2_COMPARISON.es.md"}
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".git", "build"}
PKGS = ["numpy", "pandas", "pyyaml", "matplotlib", "nbformat", "nbconvert", "ipykernel", "pytest"]
VARIANTS = ["v_full", "v_milestone", "v_snapshot", "v_no_automated", "v_no_appointments"]
EXPECTED_COUNTS = {"v_full": (8, 0), "v_milestone": (8, 0), "v_snapshot": (6, 2), "v_no_automated": (6, 2), "v_no_appointments": (7, 1)}


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
    return {rel: sha(p) for rel, p in tree_files() if rel.startswith(("baseline/", "reports/f1/", "reports/f2/"))}


def frozen_problems(h):
    f0 = manifest(ROOT / "baseline" / "MANIFEST.sha256")
    expected = {**{k: v for k, v in f0.items() if k.startswith("baseline/")}, **FROZEN_OUTSIDE_F0_MANIFEST}
    probs = [f"{rel} differs from its frozen hash" for rel, ref in expected.items() if h.get(rel) != ref]
    probs += [f"unexpected file {r}" for r in sorted(set(h) - set(expected))]
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
    for rel in ("data", "notebooks/admissions_analysis.ipynb", "build", ".pytest_cache",
                *sorted(p.relative_to(ROOT).as_posix() for p in OUT.glob("*") if p.relative_to(ROOT).as_posix() != F3_PREV_MANIFEST)):
        p = ROOT / rel
        if p.is_dir():
            shutil.rmtree(p); removed.append(rel + "/")
        elif p.exists():
            p.unlink(); removed.append(rel)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    log.append({"step": "clean", "cmd": "remove data/, notebook, build/, caches, reports/f3/ (except the v1.3.0 manifest)", "exit": 0,
                "secs": round(time.time() - t0, 1), "out": ", ".join(removed)})
    print("[clean] removed:", ", ".join(removed))


def classify(ref=None, declared_modified=DECLARED_MODIFIED, declared_new=DECLARED_NEW):
    ref = ref if ref is not None else manifest(ROOT / "reports" / "f2" / "MANIFEST_F2.sha256")
    now = {rel: sha(p) for rel, p in tree_files()}
    rows, problems = [], []
    for rel in sorted(set(ref) | set(now)):
        if rel in REPORT_FILES or rel.startswith("reports/f2/"):
            continue                                   # reports/f2/ is checked as frozen, file by file
        r, c = ref.get(rel), now.get(rel)
        if r and c == r:
            status = "unchanged"
        elif r and c is None:
            status = "REMOVED"; problems.append(rel)
        elif r and rel in declared_modified:
            status = "modified (declared)"
        elif r:
            status = "MODIFIED (undeclared)"; problems.append(rel)
        elif rel in declared_new:
            status = "new (declared)"
        else:
            status = "NEW (undeclared)"; problems.append(rel)
        rows.append({"file": rel, "status": status, "ref": r, "cur": c})
    return rows, problems


def reconcile():
    sys.path.insert(0, str(ROOT / "src"))
    import metrics
    from canonical import mapping
    from canonical.adapters import admissions as ad
    from canonical.validate import validate
    from kpispec import engine
    from kpispec.spec import load_spec
    spec = load_spec(ROOT / "profiles" / "admissions" / "kpis.yaml")
    ids = list(spec.kpis)
    f0 = {m["id"]: m for m in json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8"))["metrics"]}
    f1_text = (ROOT / "reports" / "f1" / "metrics_f1.json").read_text(encoding="utf-8")
    f1 = {m["id"]: m for m in json.loads(f1_text)["metrics"]}
    f2 = {m["id"]: {k: v for k, v in m.items() if k != "status"}
          for m in json.loads((ROOT / "reports" / "f2" / "metrics_f2_canonical.json").read_text(encoding="utf-8"))["baseline_metrics"]}
    ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
    live = {m.id: m.to_dict() for m in metrics.baseline_metrics(ctx)}
    direct_doc = metrics.baseline_document(ctx, F1_ID, ROOT)
    direct_identical = json.dumps(direct_doc, indent=2, ensure_ascii=False) + "\n" == f1_text
    rec_direct = metrics.reconcile(direct_doc, {"metrics": list(f0.values())})
    can = validate(mapping.map_directory(ROOT / "data"))
    ad.check_profile(can)
    canon = ad.evaluate(can)
    rec_canon = metrics.reconcile({"metrics": [{k: v for k, v in e.items() if k != "status"} for e in canon["baseline_metrics"]]},
                                  {"metrics": list(f0.values())})
    res = engine.evaluate(spec, can)
    eng = {r["id"]: engine.baseline_shape(spec, r) for r in res if r["status"] == "available"}
    rows = []
    for kid in ids:
        e = eng.get(kid)
        rows.append({"id": kid, "engine": e, "f0": e == f0[kid], "f1": e == f1[kid], "f2": e == f2[kid],
                     "metrics_py": e == live[kid], "reference_value": f0[kid]["value"],
                     "numerator": f0[kid]["numerator_value"], "denominator": f0[kid]["denominator_value"]})
    exp = json.loads((ROOT / "tests" / "fixtures" / "canonical_handcalc" / "expected.json").read_text(encoding="utf-8"))
    ref = {**exp["metrics_all_eligible"], **exp["metrics_mature_eligible"],
           "eligible_leads": {"value": exp["populations"]["eligible"], "numerator": exp["populations"]["eligible"], "denominator": None}}
    r6 = lambda v: round(v, 6) if isinstance(v, float) else v
    variants = {}
    for name in VARIANTS:
        c = ad.load(ROOT / "tests" / "fixtures" / "canonical_handcalc" / name)
        out = {r["id"]: r for r in engine.evaluate(spec, c)}
        na_exp = {e["id"]: e["reason"] for e in exp["variants"][name]["not_available"]}
        problems = []
        for kid in ids:
            r = out[kid]
            if kid in na_exp:
                if not (r["status"] == "not_available" and r["reason"] == na_exp[kid]):
                    problems.append(kid)
            elif r["status"] != "available" or {f: r6(r[f]) for f in ("value", "numerator", "denominator")} != \
                    {f: r6(ref[kid][f]) for f in ("value", "numerator", "denominator")}:
                problems.append(kid)
        avail = sum(r["status"] == "available" for r in out.values())
        variants[name] = {"available": avail, "not_available": len(out) - avail,
                          "counts_as_planned": (avail, len(out) - avail) == EXPECTED_COUNTS[name],
                          "mismatches": problems, "results": [out[k] for k in ids]}
    engine_doc = {"version_id": VERSION_ID, "spec": "profiles/admissions/kpis.yaml (kpi-spec/0.1)",
                  "route": "CSV -> canonical dataset -> src/kpispec engine (src/metrics.py not imported, directly or indirectly)",
                  "note": metrics.SYNTHETIC_NOTE, "results": [eng.get(k) or next(r for r in res if r["id"] == k) for k in ids]}
    return {"rows": rows, "variants": variants, "engine_doc": engine_doc, "direct_identical": direct_identical,
            "rec_direct": rec_direct, "rec_canon": rec_canon}


def f3_manifest():
    lines = [f"{sha(p)}  {rel}" for rel, p in tree_files() if rel not in REPORT_FILES]
    text = "\n".join(lines) + "\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def parse_pytest(out):
    g = lambda k: int(m.group(1)) if (m := re.search(rf"(\d+) {k}", out)) else 0
    return g("passed"), g("failed"), g("xfailed"), g("xpassed")


def write_reports(log, env, env_diffs, rows, R, tree_id, check_result, fz_before, fz_after, fz_probs):
    when = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    passed, failed, xfailed, xpassed = parse_pytest(next(s["out"] for s in log if s["step"] == "tests"))
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    count_txt = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    md47 = int(R["rec_direct"].match.astype(bool).sum()); mc47 = int(R["rec_canon"].match.astype(bool).sum())
    ok8 = sum(all(r[k] for k in ("f0", "f1", "f2", "metrics_py")) for r in R["rows"])
    fmt = lambda v: "—" if v is None else v
    for lang in ("en", "es"):
        es = lang == "es"
        T = (lambda e, s: s) if es else (lambda e, s: e)
        sfx = ".es" if es else ""
        steps = "\n".join(f"| {i + 1} | `{s['cmd']}` | {s['exit']} | {s['secs']} |" for i, s in enumerate(log))
        envtxt = ", ".join(f"{k}=={v}" for k, v in env.items())
        envchk = T("identical to baseline/environment.txt", "idéntico a baseline/environment.txt") if not env_diffs else str(env_diffs)
        chk = check_result[lang] if check_result else T("not run in this mode (use --check)", "no ejecutada en este modo (usar --check)")
        frozen_line = (T("byte-identical before and after; pinned hashes verified", "idénticos byte a byte antes y después; hashes fijados verificados")
                       if fz_before == fz_after and not fz_probs else T("PROBLEM: ", "PROBLEMA: ") + "; ".join(fz_probs or ["changed"]))
        krows = "\n".join(
            f"| `{r['id']}` | {fmt(r['reference_value'])} | {fmt(r['numerator'])} / {fmt(r['denominator'])} | "
            f"{fmt(r['engine']['value']) if r['engine'] else 'n/a'} | {'✓' if r['f0'] else '✗'} | {'✓' if r['f1'] else '✗'} | "
            f"{'✓' if r['f2'] else '✗'} | {'✓' if r['metrics_py'] else '✗'} |" for r in R["rows"])
        vrows = []
        for name, v in R["variants"].items():
            na = ", ".join(f"`{x['id']}` {x['reason']}" for x in v["results"] if x["status"] == "not_available") or "—"
            vrows.append(f"| `{name}` | {v['available']} / {v['not_available']} | {na} | "
                         f"{'✓' if v['counts_as_planned'] and not v['mismatches'] else '✗ ' + ', '.join(v['mismatches'])} |")
        vrows = "\n".join(vrows)
        mod = "\n".join(f"- `{r['file']}` — {DECLARED_MODIFIED[r['file']]}" for r in rows if r["status"] == "modified (declared)")
        new = "\n".join(f"- `{r['file']}`" for r in rows if r["status"] == "new (declared)")
        intact = "\n".join(f"- `{r['file']}`" for r in rows if r["status"] == "unchanged")
        prows = R["prev_rows"]
        pcount = {}
        for r in prows:
            pcount[r["status"]] = pcount.get(r["status"], 0) + 1
        pcount_txt = ", ".join(f"{k}: {v}" for k, v in sorted(pcount.items()))
        pmod = "\n".join(f"- `{r['file']}` — {DECLARED_MODIFIED_VS_F3_PREV[r['file']]}" for r in prows if r["status"] == "modified (declared)")
        pnew = "\n".join(f"- `{r['file']}`" for r in prows if r["status"] == "new (declared)") or "—"
        report = f"""{T('**Language:** English | [Español](F3_REPORT.es.md)', '**Idioma:** [English](F3_REPORT.md) | Español')}

# {T('F3.0 — run report', 'F3.0 — informe de ejecución')} (`{VERSION_ID}`)

{T('Generated by', 'Generado por')} `python scripts/f3_run.py{' --check' if check_result else ''}` · {when}.
{T('All data and figures are synthetic (seed 42 and the official 12-record hand fixture). Admissions profile only; no portability claim; no CRM, no real data.',
   'Todos los datos y cifras son sintéticos (semilla 42 y el fixture oficial de 12 registros hecho a mano). Solo el perfil de admisiones; sin afirmaciones de portabilidad; sin CRM ni datos reales.')}

{T('F3.0 declares eight KPIs in `profiles/admissions/kpis.yaml` (kpi-spec/0.1, closed language: five operations, AND-only filters, no expressions, no OR, no code) and evaluates them with `src/kpispec` in parallel with `src/metrics.py`, which remains the official reference and is not modified. Details: `docs/kpi_spec.md`.',
   'F3.0 declara ocho KPIs en `profiles/admissions/kpis.yaml` (kpi-spec/0.1, lenguaje cerrado: cinco operaciones, filtros solo con Y, sin expresiones, sin OR, sin código) y los evalúa con `src/kpispec` en paralelo con `src/metrics.py`, que sigue siendo la referencia oficial y no se modifica. Detalles: `docs/kpi_spec.es.md`.')}

## {T('Version', 'Versión')}

| {T('Item', 'Elemento')} | {T('Value', 'Valor')} |
|---|---|
| {T('F3 id', 'Identificador F3')} | `{VERSION_ID}` |
| {T('F3 tree id (SHA-256 of', 'Tree id F3 (SHA-256 de')} `reports/f3/MANIFEST_F3.sha256`) | `{tree_id}` |
| {T('Frozen references', 'Referencias congeladas')} | `{F0_ID}` `{F0_TREE_ID[:16]}…` · `{F1_ID}` `{F1_TREE_ID[:16]}…` · `{F2_ID}` `{F2_TREE_ID[:16]}…` |
| {T('Contract / spec', 'Contrato / especificación')} | `crm-canonical/0.1.1` ({T('unchanged', 'sin cambios')}) · `kpi-spec/0.1` ({T('new', 'nueva')}) |
| Git | {T('no commit or tag (not a git repository; not authorised)', 'sin commit ni tag (no es un repositorio git; no autorizado)')} |
| {T('Environment', 'Entorno')} | {envtxt} — {envchk} |

## {T('Commands and results', 'Comandos y resultados')}

| # | {T('Command', 'Comando')} | exit | {T('seconds', 'segundos')} |
|---|---|---|---|
{steps}

| {T('Check', 'Comprobación')} | {T('Result', 'Resultado')} |
|---|---|
| {T('Tests', 'Pruebas')} | **{passed} passed, {failed} failed, {xfailed} xfailed, {xpassed} xpassed** |
| {T('Eight engine KPIs = F0, F1, F2 and src/metrics.py', 'Ocho KPIs del motor = F0, F1, F2 y src/metrics.py')} | **{ok8} / {len(R['rows'])}** {T('(value at 6 decimals, numerator, denominator, descriptive fields)', '(valor a 6 decimales, numerador, denominador, campos descriptivos)')} |
| {T('47 metrics of src/metrics.py vs F0, direct / canonical route', '47 métricas de src/metrics.py frente a F0, ruta directa / canónica')} | **{md47} / 47** · **{mc47} / 47** |
| {T('F1 document generated in memory = reports/f1/metrics_f1.json (never written)', 'Documento F1 generado en memoria = reports/f1/metrics_f1.json (nunca se escribe)')} | {T('byte-identical', 'idéntico byte a byte') if R['direct_identical'] else T('DIFFERENT', 'DISTINTO')} |
| {T('Frozen: baseline/ (F0), reports/f1/ (F1), reports/f2/ (F2)', 'Congelados: baseline/ (F0), reports/f1/ (F1), reports/f2/ (F2)')} | {frozen_line} ({len(fz_after)} {T('files', 'archivos')}) |
| {T('Reproducibility', 'Reproducibilidad')} | {chk} |

## {T('Eight KPIs on the generated data', 'Ocho KPIs con los datos generados')}

| KPI | {T('reference value (F0)', 'valor de referencia (F0)')} | {T('num. / den.', 'num. / den.')} | {T('engine', 'motor')} | = F0 | = F1 | = F2 | = metrics.py |
|---|---|---|---|---|---|---|---|
{krows}

## {T('Official fixture (12 records), five variants, engine only', 'Fixture oficial (12 registros), cinco variantes, solo el motor')}

| {T('Variant', 'Variante')} | {T('available / not available', 'disponibles / no disponibles')} | {T('not available (reason)', 'no disponibles (motivo)')} | {T('= hand values and approved matrix', '= valores a mano y matriz aprobada')} |
|---|---|---|---|
{vrows}

## {T('Eligibility, fields and ratios', 'Elegibilidad, campos y ratios')}

{T('For the admissions profile, record_origin = original is exactly the F0 eligibility (is_duplicate = false and is_reactivation = false): the mapping derives record_origin from the two flags and rejects rows with both. tests/test_kpi_eligibility.py and tests/test_kpi_requirements.py check the equivalence on the generated data (against the F0 loader), on the canonical path (CSV -> canonical -> adapter), on the 12-record fixture and on all five fixture variants; an unknown or null origin is a data error (E_ENUM in the contract, K_FIELD_VALUE in the engine) and a missing origin field is FLD, so no record enters eligible silently. It is a profile rule, not an engine rule.',
   'En el perfil de admisiones, record_origin = original es exactamente la elegibilidad de F0 (is_duplicate = false e is_reactivation = false): el mapeo deriva record_origin de los dos indicadores y rechaza las filas con ambos. tests/test_kpi_eligibility.py y tests/test_kpi_requirements.py comprueban la equivalencia con los datos generados (frente al cargador de F0), por el camino canónico (CSV -> canónico -> adaptador), en el fixture de 12 registros y en las cinco variantes del fixture; un origen desconocido o nulo es un error de datos (E_ENUM en el contrato, K_FIELD_VALUE en el motor) y si falta el campo de origen el resultado es FLD, así que ningún registro entra en eligible sin avisar. Es una regla del perfil, no del motor.')}

{T('No field is assumed available: a field not provided gives FLD with the exact missing fields, combined with HM, HF, AUT, APT, DEN0, INSUF or ORD when relevant. Ratios need the same unit and a declared relation (subset_of, same_base, independent_allowed); forms_over_interviews_held is same_base.',
   'Ningún campo se da por disponible: un campo no proporcionado da FLD con la lista exacta de campos que faltan, combinado con HM, HF, AUT, APT, DEN0, INSUF u ORD cuando corresponde. Los ratios exigen la misma unidad y una relación declarada (subset_of, same_base, independent_allowed); forms_over_interviews_held es same_base.')}

## {T('Limits', 'Límites')}

{T('time_model naive_wall_clock only: UTC instants and local-calendar rules are F3.5 (decided, not yet authorised; no UTC code in F3.0); the UTC adapter is still not supported. The other 27 parametrisable KPIs are F3.1 (not authorised). No readiness for real data or CRM connections is claimed.',
   'Solo time_model naive_wall_clock: los instantes UTC y las reglas de calendario local son F3.5 (decidida, todavía no autorizada; F3.0 no contiene código UTC); el adaptador UTC sigue sin estar soportado. Los otros 27 KPIs parametrizables son F3.1 (no autorizada). No se afirma preparación para datos reales ni para conexiones CRM.')}

## {T('Files against F2', 'Archivos frente a F2')} (`reports/f2/MANIFEST_F2.sha256`, `{F2_ID}`)

{count_txt}. {T('Modified:', 'Modificados:')}

{mod}

{T('New:', 'Nuevos:')}

{new}

{T('Intact (byte-identical to F2):', 'Intactos (idénticos byte a byte a F2):')}

{intact}

{T('Per-file hashes:', 'Hashes por archivo:')} [`F2_COMPARISON{sfx}.md`](F2_COMPARISON{sfx}.md).

## {T('Changes against', 'Cambios frente a')} `{F3_PREV_ID}` (`{F3_PREV_MANIFEST}`, tree id `{F3_PREV_TREE_ID[:16]}…`, {T('pinned', 'fijado')})

{pcount_txt}. {T('Modified:', 'Modificados:')}

{pmod}

{T('New:', 'Nuevos:')}

{pnew}

{T('Every other file is byte-identical to', 'Todos los demás archivos son idénticos byte a byte a')} `{F3_PREV_ID}`.
"""
        (OUT / f"F3_REPORT{sfx}.md").write_text(report, encoding="utf-8")
        frow = "\n".join(f"| `{r['file']}` | {r['status']} | `{(r['ref'] or '—')[:16]}` | `{(r['cur'] or '—')[:16]}` | "
                         f"{DECLARED_MODIFIED.get(r['file'], '') if r['status'].startswith('modified') else ''} |" for r in rows)
        comp = f"""{T('**Language:** English | [Español](F2_COMPARISON.es.md)', '**Idioma:** [English](F2_COMPARISON.md) | Español')}

# {VERSION_ID} {T('vs', 'frente a')} {F2_ID}

{T('Reference', 'Referencia')}: `reports/f2/MANIFEST_F2.sha256` (tree id `{F2_TREE_ID}`). {T('reports/f2/ itself is checked file by file against pinned hashes (see F3_REPORT).', 'reports/f2/ se comprueba archivo a archivo contra hashes fijados (ver F3_REPORT).')} {count_txt}.

| {T('File', 'Archivo')} | {T('Status', 'Estado')} | SHA-256 {F2_ID} | SHA-256 {VERSION_ID} | {T('Declared change', 'Cambio declarado')} |
|---|---|---|---|---|
{frow}
"""
        (OUT / f"F2_COMPARISON{sfx}.md").write_text(comp, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if (ROOT / "scripts" / "release_run.py").exists():   # v1.4.0-gh guard, before touching any file
        raise SystemExit("reports/f3/ is frozen since v1.4.0-gh: verify F3 from admissions-crm-analytics-v1.3.1-f3.zip "
                         "(python scripts/f3_run.py --check in a clean folder); this tree is checked by "
                         "python scripts/release_run.py --check")
    stored = (OUT / "MANIFEST_F3.sha256").read_text() if (OUT / "MANIFEST_F3.sha256").exists() else None
    if args.check and stored is None:
        raise SystemExit("no stored reports/f3/MANIFEST_F3.sha256 to check against")
    env, env_diffs = environment()
    print("[environment]", "matches baseline/environment.txt" if not env_diffs else f"DIFFERS: {env_diffs}")
    fz_before = frozen_hashes()
    probs = frozen_problems(fz_before)
    if probs:
        raise SystemExit("frozen references differ before the run: " + "; ".join(probs))
    prev_path = ROOT / F3_PREV_MANIFEST
    if not prev_path.exists() or sha(prev_path) != F3_PREV_TREE_ID:
        raise SystemExit(f"{F3_PREV_MANIFEST} missing or differs from the pinned {F3_PREV_ID} tree id")
    print(f"[frozen] F0, F1 and F2 verified ({len(fz_before)} files); {F3_PREV_ID} manifest verified")

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
    run("map", [sys.executable, "scripts/map_to_canonical.py"], log)
    tests_out = run("tests", [sys.executable, "-m", "pytest", "-q"], log)
    if parse_pytest(tests_out)[2] or parse_pytest(tests_out)[3]:
        raise SystemExit("xfail / xpass found: every test must pass normally")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)

    R = reconcile()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "kpi_engine_results.json").write_text(json.dumps(R["engine_doc"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "kpi_handcalc_variants.json").write_text(json.dumps(R["variants"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)

    rows, problems = classify()
    prev_rows, prev_problems = classify(manifest(prev_path), DECLARED_MODIFIED_VS_F3_PREV, DECLARED_NEW_VS_F3_PREV)
    R["prev_rows"] = prev_rows
    problems += [f"vs {F3_PREV_ID}: {p}" for p in prev_problems]
    if sha(prev_path) != F3_PREV_TREE_ID:
        problems.append(f"{F3_PREV_MANIFEST} changed during the run")
    fz_after = frozen_hashes()
    fz_probs = frozen_problems(fz_after)
    text, tree_id = f3_manifest()
    check_result = None
    if args.check:
        old, new = manifest_text(stored), manifest_text(text)
        diff = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        check_result = ({"en": f"identical to the stored F3 manifest ({len(new)} files) — tree id {tree_id[:16]}",
                         "es": f"idéntica al manifiesto F3 guardado ({len(new)} archivos) — tree id {tree_id[:16]}"}
                        if not diff else {"en": "DRIFT in: " + ", ".join(diff), "es": "DIFERENCIAS en: " + ", ".join(diff)})
        print("[check]", check_result["en"])
        (OUT / "MANIFEST_F3.sha256").write_text(stored, encoding="utf-8")
    else:
        (OUT / "MANIFEST_F3.sha256").write_text(text, encoding="utf-8")
    write_reports(log, env, env_diffs, rows, R, tree_id, check_result, fz_before, fz_after, fz_probs)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    ok8 = all(all(r[k] for k in ("f0", "f1", "f2", "metrics_py")) for r in R["rows"])
    okv = all(v["counts_as_planned"] and not v["mismatches"] for v in R["variants"].values())
    ok47 = R["direct_identical"] and bool(R["rec_direct"].match.astype(bool).all()) and bool(R["rec_canon"].match.astype(bool).all())
    print(f"[compare] vs F2: {problems or 'no problems'} · frozen unchanged: {fz_before == fz_after and not fz_probs}")
    print(f"[kpis] engine = F0/F1/F2/metrics.py: {sum(all(r[k] for k in ('f0', 'f1', 'f2', 'metrics_py')) for r in R['rows'])}/8 · 47 metrics ok: {ok47}")
    print("[variants] " + " · ".join(f"{k} {v['available']}/{v['not_available']}{'' if not v['mismatches'] else ' MISMATCH'}" for k, v in R["variants"].items()))
    print(f"F3 {VERSION_ID} · tree id {tree_id}")
    if problems or fz_before != fz_after or fz_probs or not (ok8 and okv and ok47) or \
            (check_result and check_result["en"].startswith("DRIFT")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
