"""Full reproduction of the GitHub preparation (v1.4.4-gh), compared with the frozen F0, F1, F2 and F3 references.

Reproducción completa de la preparación para GitHub (v1.4.4-gh), comparada con F0, F1, F2 y F3 congeladas.

Two verification levels (v1.4.3-gh), always reported separately:
  * analytical (portable): data bytes, the 47 metrics and the eight KPIs, every notebook cell, text, table and number,
    execution without errors, the structure of the charts (data, titles, labels; scripts/chart_signature.py), tests,
    documents, frozen references and the stored manifest;
  * graphical (strict): the executed notebook is byte-identical to F1, PNG images included.
--mode strict (default) requires both. --mode portable requires the analytical level and reports PNG differences
separately; it is not a byte-for-byte reproduction of the notebook, it never overwrites the versioned notebook or
figures, never writes reports/release/, and writes its report to build/portable/ (ignored by Git, outside every
reference manifest). Any other notebook difference (code, text, numbers, metadata) fails both modes.

Steps (real subprocesses; exit codes and durations are recorded):
  0. environment  installed versions vs baseline/environment.txt (reported)
  1. frozen       baseline/ (F0), reports/f1/ (F1), reports/f2/ (F2) and reports/f3/ (F3, v1.3.1-f3) vs pinned hashes
  2. clean        remove data/, the executed notebook, docs/img/*.png, build/, caches and the generated files of
                  reports/release/ — automatically, nothing has to be deleted by hand; never a frozen folder
  3. generate     python src/generate_data.py; CSV bytes must equal the F0 manifest
  4. notebook     python scripts/build_notebook.py, with the project's reference chart rendering (bundled Inter fonts,
                  scripts/notebook_rendering.py); notebook bytes must equal the F1 manifest (if not, the report says
                  whether only the PNG images differ; the step still fails)
  5. figures      python scripts/export_figures.py (README figures, extracted from the notebook)
  6. map          python scripts/map_to_canonical.py -> build/ (ignored by Git)
  7. tests        python -m pytest -q (no xfail / xpass allowed)
  8. read-only    python scripts/show_results.py (en, es, --all): the file tree is identical before and after
  9. reconcile    the eight declarative KPIs vs F0, F1, F2 and src/metrics.py; the 47 metrics vs F0 (direct and
                  canonical routes); the five fixture variants (same checks as F3, imported from scripts/f3_run.py)
 10. documents    README results blocks = computed results; internal links resolve; figures = notebook outputs
 11. security     pattern scan (secrets, personal data, local paths, notebook metadata) — not a guarantee
 12. compare      every repository file vs reports/f3/MANIFEST_F3.sha256 and vs the v1.4.0-gh manifest
                  (reports/release/MANIFEST_RELEASE_v1.4.0.sha256), both read only: unchanged / modified (declared) /
                  new (declared); anything else fails
 13. outputs      reports/release/: MANIFEST_RELEASE.sha256, RELEASE_REPORT(.es).md, F3_COMPARISON(.es).md

If any step fails, the versioned generated files (data/*.csv, the executed notebook, docs/img/*.png and the stored
reports/release/ files) are put back exactly as they were before the run, so a failed run never leaves the folder
modified.

Usage:
  python scripts/release_run.py          # create / refresh the release manifest and reports
  python scripts/release_run.py --check  # same clean run, then require the stored release manifest (exit 1 on drift)
  python scripts/release_run.py --mode portable   # analytical verification on any system; PNG differences reported
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import release_checks as rc  # noqa: E402

OUT = ROOT / "reports" / "release"
PORTABLE_OUT = ROOT / "build" / "portable"   # portable-mode reports: ignored by Git, outside every reference manifest
VERSION_ID = "v1.4.4-gh"
# previous release, compared file by file (read only); its manifest is kept and never rewritten
GH0_ID = "v1.4.3-gh"
GH0_MANIFEST = "reports/release/MANIFEST_RELEASE_v1.4.3.sha256"
GH0_TREE_ID = "a9da920c3e2e8a3b7ee6fed8fff5875faf25fd2b05ebe840c859e3841c232d7b"
# every kept release manifest, pinned (never rewritten or removed by the clean step)
KEPT_MANIFESTS = {"reports/release/MANIFEST_RELEASE_v1.4.0.sha256": "e1c13bfa5390ed5128970700941e63887ed999f6304cc1b96e946b0479b4a41d",
                  "reports/release/MANIFEST_RELEASE_v1.4.1.sha256": "a2e68371cadd318a0d2d72d33d55663ab68d41dea2d7706253cbcbb927d9c7bb",
                  "reports/release/MANIFEST_RELEASE_v1.4.2.sha256": "98841cc859eec50fb11a2772263dbc1595f16ce4a86952584729791e1c8096c2",
                  GH0_MANIFEST: GH0_TREE_ID}
F3_ID = "v1.3.1-f3"
F3_TREE_ID = "f1a73209cfaf24d3768784e121f376e1d0ec485eca31ddd22f2b57e09ef23c34"
F3_REPORTS = {
    "reports/f3/F2_COMPARISON.es.md": "b5d778d503c40010e32eea93ccd47fdc8b2790ea665fd480c2acbb2aad07690c",
    "reports/f3/F2_COMPARISON.md": "b060204725e9199f73cdf88870f051ce4d188ab7443afb71e4950e5a7d278c33",
    "reports/f3/F3_REPORT.es.md": "327e55008250cfae29a56c8398c4bd20b73b2432a630cf5b356d6b1875245556",
    "reports/f3/F3_REPORT.md": "133116b856e233826e5cea2e99634575e1f26fb81009ef2f721f4425d35ba9d7",
    "reports/f3/MANIFEST_F3.sha256": F3_TREE_ID,
    "reports/f3/MANIFEST_F3_v1.3.0.sha256": "b189d44e9d092d3481817a28e7fcca98535cf311286affa079bf5af1d560e1bd",
    "reports/f3/kpi_engine_results.json": "97a2f7d7a9175ae919291407a9e6040f38d01954abae9fd965cec0861a624af9",
    "reports/f3/kpi_handcalc_variants.json": "6d323e1dd01543a9c4e5f9cd4206e3a61aa65d830c0b8e34351a9d13fad00e96",
}
DECLARED_MODIFIED = {
    ".gitignore": "virtual environments, secrets, local copies (*.zip, *.diff), editors and build/ added; original four rules kept",
    "README.md": "rewritten for visitors: problem, what it does, how to run, results, scope; phase history moved to links",
    "README.es.md": "reescrito para visitantes: problema, qué hace, cómo ejecutarlo, resultados, alcance; historial enlazado",
    "docs/PROJECT_STATUS.md": "v1.4.0-gh and v1.4.1-gh rows, GitHub preparation decisions, open items, B pending",
    "docs/PROJECT_STATUS.es.md": "filas v1.4.0-gh y v1.4.1-gh, decisiones de preparación, pendientes, B pendiente",
    "src/generate_data.py": "authorised line-ending fix: lineterminator=\"\\n\" in the three CSV writes (same bytes on Linux)",
    "scripts/build_notebook.py": "authorised fixes: notebook written through a file opened with newline=\"\\n\"; reference chart rendering applied in the kernel before the first cell (cells unchanged; same notebook bytes as F1)",
    "scripts/f3_run.py": "guard only: refuses to run on this tree before touching any file (reports/f3/ is frozen)",
    "tests/test_regression_f0.py": "recognises the declared v1.4.0-gh changes of src/generate_data.py and .gitignore (new hashes pinned)",
    "tests/test_regression_f1.py": "recognises the declared v1.4.0-gh changes (new hashes of code files pinned)",
    "tests/test_regression_f2.py": "recognises the declared changes; v1.4.1-gh: path comparison with uniform relative POSIX paths and a separator test",
    "tests/test_integrity.py": "v1.4.2-gh authorised compatibility fix: lineterminator=\"\\n\" in the temporary CSV write of test_regeneration_is_reproducible; byte-for-byte comparison unchanged",
}
DECLARED_NEW = {
    ".gitattributes", "requirements-lock.txt", "CHANGELOG.md", ".github/workflows/tests.yml",
    "scripts/show_results.py", "scripts/export_figures.py", "scripts/release_run.py", "scripts/release_checks.py",
    "docs/analytical_decisions.md", "docs/analytical_decisions.es.md",
    "docs/img/funnel_mature_cohorts.png", "docs/img/main_kpi_by_cohort.png", "docs/img/show_rate_by_month.png",
    "tests/release_declared.py", "tests/test_release.py", "tests/test_regression_f3.py", "tests/test_serialization.py",
    # v1.4.1-gh
    "assets/fonts/inter/Inter-Regular.otf", "assets/fonts/inter/Inter-Bold.otf", "assets/fonts/inter/OFL.txt",
    "assets/fonts/inter/FONTS.md", "scripts/notebook_rendering.py",
    "tests/test_rendering.py", "reports/release/MANIFEST_RELEASE_v1.4.0.sha256",
    # v1.4.2-gh
    "reports/release/MANIFEST_RELEASE_v1.4.1.sha256",
    # v1.4.3-gh
    "reports/release/MANIFEST_RELEASE_v1.4.2.sha256", "scripts/chart_signature.py", "tests/chart_signature_reference.json",
    "tests/test_validation_modes.py",
    # v1.4.4-gh
    GH0_MANIFEST, "LICENSE", "LICENSE-CONTENT", "tests/test_licenses.py",
}
# v1.4.4-gh against v1.4.3-gh (reports/release/MANIFEST_RELEASE_v1.4.3.sha256, read only): licences and documentation
DECLARED_MODIFIED_VS_GH0 = {
    "README.md": "licence section (MIT / CC BY 4.0 / SIL OFL 1.1); Windows 11 portable analytical result reported by the project owner; notebook viewing note (JupyterLab optional)",
    "README.es.md": "sección de licencias (MIT / CC BY 4.0 / SIL OFL 1.1); resultado analítico portable de Windows 11 informado por la responsable; nota sobre la visualización del notebook (JupyterLab opcional)",
    "docs/PROJECT_STATUS.md": "v1.4.4-gh row; licence decision; decisions of 2026-10-15; Windows result; next step",
    "docs/PROJECT_STATUS.es.md": "fila v1.4.4-gh; decisión de licencia; decisiones del 2026-10-15; resultado de Windows; siguiente paso",
    "CHANGELOG.md": "v1.4.4-gh row",
    "scripts/release_run.py": "version identification v1.4.4-gh and declarations of this revision",
    "tests/test_release.py": "v1.4.4-gh in the version list; LICENSE and LICENSE-CONTENT in the repository top level",
}
DECLARED_NEW_VS_GH0 = {GH0_MANIFEST, "LICENSE", "LICENSE-CONTENT", "tests/test_licenses.py"}
REPORT_FILES = rc.RELEASE_OUTPUTS
TEXT_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def _f3():
    spec = importlib.util.spec_from_file_location("f3_run", ROOT / "scripts" / "f3_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F3 = _f3()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def manifest_text(text):
    return {p: h for h, p in (l.split("  ", 1) for l in text.strip().splitlines())}


def frozen_hashes():
    return {rel: sha(p) for rel, p in rc.repo_files()
            if rel.startswith(("baseline/", "reports/f1/", "reports/f2/", "reports/f3/")) or rel in KEPT_MANIFESTS}


def frozen_problems(h):
    f0 = manifest_text((ROOT / "baseline" / "MANIFEST.sha256").read_text(encoding="utf-8"))
    expected = {**{k: v for k, v in f0.items() if k.startswith("baseline/")}, **F3.FROZEN_OUTSIDE_F0_MANIFEST, **F3_REPORTS,
                **KEPT_MANIFESTS}
    probs = [f"{rel} differs from its frozen hash" for rel, ref in expected.items() if h.get(rel) != ref]
    probs += [f"unexpected file {r}" for r in sorted(set(h) - set(expected))]
    return probs


def tree_snapshot():
    """Every file and directory under the project (including ignored and cache files), with file hashes."""
    snap = {}
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if ".git" in rel.split("/"):
            continue
        snap[rel] = sha(p) if p.is_file() else "dir"
    return snap


def run(name, cmd, log, check=True):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=TEXT_ENV)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines() if "running over TCP" not in l)
    log.append({"step": name, "cmd": " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)),
                "exit": p.returncode, "secs": round(time.time() - t0, 1), "out": out.strip()})
    print(f"[{name}] exit={p.returncode} ({log[-1]['secs']} s)")
    if p.returncode != 0 and check:
        print(out)
        raise SystemExit(f"step {name} failed")
    return out


def clean(log, keep_release_reports=False):
    t0, removed = time.time(), []
    targets = ["data", "notebooks/admissions_analysis.ipynb", "build", ".pytest_cache",
               *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs" / "img").glob("*.png")),
               *([] if keep_release_reports else      # portable mode never touches reports/release/
                 sorted(p.relative_to(ROOT).as_posix() for p in OUT.glob("*") if p.relative_to(ROOT).as_posix() not in KEPT_MANIFESTS))]
    for rel in targets:
        p = ROOT / rel
        if p.is_dir():
            shutil.rmtree(p); removed.append(rel + "/")
        elif p.exists():
            p.unlink(); removed.append(rel)
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    log.append({"step": "clean", "cmd": "remove data/, notebook, docs/img/*.png, build/, caches"
                + ("" if keep_release_reports else ", reports/release/*"),
                "exit": 0, "secs": round(time.time() - t0, 1), "out": ", ".join(removed)})
    print("[clean] removed:", ", ".join(removed))


def _without_png(nb: dict) -> dict:
    nb = json.loads(json.dumps(nb))
    for c in nb["cells"]:
        for o in c.get("outputs", []):
            if "image/png" in o.get("data", {}):
                o["data"]["image/png"] = "<png>"
    return nb


def notebook_diagnosis(f1_hash: str, reference: dict | None) -> str:
    """'identical', or why the rebuilt notebook differs from the F1 bytes (the step fails in both cases)."""
    nb_path = ROOT / "notebooks" / "admissions_analysis.ipynb"
    if sha(nb_path) == f1_hash:
        return "identical"
    msg = f"DIFFERENT from F1 ({sha(nb_path)[:16]} vs {f1_hash[:16]})"
    if reference is None:
        return msg + "; no F1 notebook was present before the run to compare with"
    rebuilt = json.loads(nb_path.read_text(encoding="utf-8"))
    if _without_png(rebuilt) == _without_png(reference):
        n = sum(1 for a, b in zip(*[[o["data"]["image/png"] for c in x["cells"] for o in c.get("outputs", [])
                                     if "image/png" in o.get("data", {})] for x in (rebuilt, reference)]) if a != b)
        return (msg + f"; all text and numeric outputs are identical, only {n} PNG chart image(s) differ: the chart "
                "rendering differs although the project fonts and settings were applied (scripts/notebook_rendering.py): this platform "
                "renders text differently — see README, 'What is reproduced'")
    return msg + "; text or numeric outputs differ as well"


def classify(ref, declared_modified=None, declared_new=None):
    declared_modified = DECLARED_MODIFIED if declared_modified is None else declared_modified
    declared_new = DECLARED_NEW if declared_new is None else declared_new
    now = {rel: sha(p) for rel, p in rc.repo_files()}
    rows, problems = [], []
    for rel in sorted(set(ref) | set(now)):
        if rel in REPORT_FILES or rel.startswith(("reports/f2/", "reports/f3/")):
            continue                                   # frozen report folders are checked file by file
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


def release_manifest():
    lines = [f"{sha(p)}  {rel}" for rel, p in rc.repo_files() if rel not in REPORT_FILES]
    text = "\n".join(lines) + "\n"
    return text, hashlib.sha256(text.encode()).hexdigest()


def write_reports(ctx):
    when = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    log, rows, R, scan = ctx["log"], ctx["rows"], ctx["R"], ctx["scan"]
    passed, failed, xfailed, xpassed = F3.parse_pytest(next(s["out"] for s in log if s["step"] == "tests"))
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    count_txt = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
    md47 = int(R["rec_direct"].match.astype(bool).sum()); mc47 = int(R["rec_canon"].match.astype(bool).sum())
    ok8 = sum(all(r[k] for k in ("f0", "f1", "f2", "metrics_py")) for r in R["rows"])
    portable = ctx["mode"] == "portable"
    dest = PORTABLE_OUT if portable else OUT
    base = "PORTABLE_REPORT" if portable else "RELEASE_REPORT"
    dest.mkdir(parents=True, exist_ok=True)
    nbo = ctx["nb_outcome"]
    env_lines = lambda e: ", ".join(f"{k} {v}" for k, v in e.items())
    for lang in ("en", "es"):
        es = lang == "es"
        T = (lambda e, s: s) if es else (lambda e, s: e)
        sfx = ".es" if es else ""
        steps = "\n".join(f"| {i + 1} | `{s['cmd']}` | {s['exit']} | {s['secs']} |" for i, s in enumerate(log))
        envtxt = ", ".join(f"{k}=={v}" for k, v in ctx["env"].items())
        envchk = T("identical to baseline/environment.txt", "idéntico a baseline/environment.txt") if not ctx["env_diffs"] else \
            T("DIFFERS from baseline/environment.txt: ", "DISTINTO de baseline/environment.txt: ") + str(ctx["env_diffs"])
        chk = ctx["check_result"][lang] if ctx["check_result"] else T("not run in this mode (use --check)", "no ejecutada en este modo (usar --check)")
        frozen_line = (T("byte-identical before and after; pinned hashes verified", "idénticos byte a byte antes y después; hashes fijados verificados")
                       if ctx["fz_before"] == ctx["fz_after"] and not ctx["fz_probs"] else T("PROBLEM: ", "PROBLEMA: ") + "; ".join(ctx["fz_probs"] or ["changed"]))
        vrows = "\n".join(f"| `{n}` | {v['available']} / {v['not_available']} | {'✓' if v['counts_as_planned'] and not v['mismatches'] else '✗'} |"
                          for n, v in R["variants"].items())
        mod = "\n".join(f"- `{r['file']}` — {DECLARED_MODIFIED[r['file']]}" for r in rows if r["status"] == "modified (declared)")
        new = "\n".join(f"- `{r['file']}`" for r in rows if r["status"] == "new (declared)")
        intact = "\n".join(f"- `{r['file']}`" for r in rows if r["status"] == "unchanged")
        rows0 = ctx["rows0"]
        c0 = {}
        for r in rows0:
            c0[r["status"]] = c0.get(r["status"], 0) + 1
        count0_txt = ", ".join(f"{k}: {v}" for k, v in sorted(c0.items()))
        mod0 = "\n".join(f"- `{r['file']}` — {DECLARED_MODIFIED_VS_GH0[r['file']]}" for r in rows0 if r["status"] == "modified (declared)") or "—"
        new0 = "\n".join(f"- `{r['file']}`" for r in rows0 if r["status"] == "new (declared)") or "—"
        bad = "\n".join(f"- `{r['file']}` — {r['status']}" for r in rows if r["status"] in ("REMOVED", "MODIFIED (undeclared)", "NEW (undeclared)")) or T("none", "ninguno")
        findings = "\n".join(f"- `{f['file']}`: {f['kind']} `{f['match']}`" for f in scan["findings"]) or T("none", "ninguno")
        nb = scan["notebook"]
        if nbo["identical"]:
            graph_nb = T("identical (including the 5 PNG images)", "idéntico (incluidas las 5 imágenes PNG)")
        else:
            sizes = "; ".join(f"{T('cell', 'celda')} {d['cell']}: {d['reference_size']} → {d['rebuilt_size']}" for d in nbo["png"])
            graph_nb = (T(f"**DIFFERENT**: {len(nbo['png'])} PNG image(s) differ (rebuilt notebook SHA-256 {ctx['nb_rebuilt_sha'][:16]}…, "
                          f"reference {ctx['nb_reference_sha'][:16]}…); pixel sizes reference → rebuilt: {sizes}",
                          f"**DISTINTO**: difieren {len(nbo['png'])} imagen(es) PNG (SHA-256 del notebook reconstruido {ctx['nb_rebuilt_sha'][:16]}…, "
                          f"referencia {ctx['nb_reference_sha'][:16]}…); tamaño en píxeles referencia → reconstruido: {sizes}"))
        analytic_nb = (T("identical to F1 in everything except PNG image bytes: code, text, tables, numbers, execution counts and metadata "
                         "(no volatile field is exempted)",
                         "idéntico a F1 en todo salvo los bytes de las imágenes PNG: código, texto, tablas, cifras, contadores de ejecución y "
                         "metadatos (no se exime ningún campo volátil)") if nbo["ok"] or nbo["identical"] else
                       T("DIFFERENT: ", "DISTINTO: ") + "; ".join(nbo["other"][:10]))
        if portable:
            verdict = (T(f"**Mode: portable.** Analytical verification: {'**PASSED**' if ctx['analytic_ok'] else '**NOT PASSED**'}. "
                         f"Strict graphical verification: {'passed (identical PNG)' if nbo['identical'] else '**not passed** — the PNG images differ from the reference environment'}. "
                         "This mode is **not** a byte-for-byte reproduction of the notebook; the versioned notebook and figures were not overwritten.",
                         f"**Modo: portable.** Verificación analítica: {'**APROBADA**' if ctx['analytic_ok'] else '**NO APROBADA**'}. "
                         f"Verificación gráfica estricta: {'aprobada (PNG idénticos)' if nbo['identical'] else '**no aprobada**: las imágenes PNG difieren del entorno de referencia'}. "
                         "Este modo **no** es una reproducción byte a byte del notebook; el notebook y los gráficos versionados no se han sobrescrito."))
        else:
            verdict = T("**Mode: strict** (analytical verification and byte-for-byte graphical verification).",
                        "**Modo: estricto** (verificación analítica y verificación gráfica byte a byte).")
        cmd = f"python scripts/release_run.py{' --mode portable' if portable else ''}{' --check' if (ctx['check_result'] and not portable) else ''}"
        report = f"""{T(f'**Language:** English | [Español]({base}.es.md)', f'**Idioma:** [English]({base}.md) | Español')}

# {T('GitHub preparation — run report', 'Preparación para GitHub — informe de ejecución')} (`{VERSION_ID}`, {T('portable mode', 'modo portable') if portable else T('strict mode', 'modo estricto')})

{T('Generated by', 'Generado por')} `{cmd}` · {when}.

{verdict}
{T('All data and figures are synthetic (seed 42 and the official 12-record hand fixture). Admissions profile only; no CRM; no real data; nothing published.',
   'Todos los datos y cifras son sintéticos (semilla 42 y el fixture oficial de 12 registros). Solo el perfil de admisiones; sin CRM; sin datos reales; nada publicado.')}

## {T('Version', 'Versión')}

| {T('Item', 'Elemento')} | {T('Value', 'Valor')} |
|---|---|
| {T('Release id', 'Identificador')} | `{VERSION_ID}` |
| {T('Tree id (SHA-256 of', 'Tree id (SHA-256 de')} `reports/release/MANIFEST_RELEASE.sha256`) | `{ctx['tree_id']}` |
| {T('Compared with', 'Comparado con')} | `{F3_ID}` (`reports/f3/MANIFEST_F3.sha256`, tree id `{F3_TREE_ID}`, {T('read only', 'solo lectura')}) |
| Git | {T('no repository, commit or tag (not authorised)', 'sin repositorio, commit ni tag (no autorizado)')} |
| {T('Platform', 'Plataforma')} | {ctx['platform']} |
| {T('Environment', 'Entorno')} | {envtxt} — {envchk} |

## {T('Commands and results', 'Comandos y resultados')}

| # | {T('Command', 'Comando')} | exit | {T('seconds', 'segundos')} |
|---|---|---|---|
{steps}

### {T('Analytical verification (portable)', 'Verificación analítica (portable)')}

| {T('Check', 'Comprobación')} | {T('Result', 'Resultado')} |
|---|---|
| {T('Generated CSV = F0 bytes', 'CSV generados = bytes de F0')} | {T('identical', 'idénticos')} |
| {T('Notebook executed without errors', 'Notebook ejecutado sin errores')} | {T('yes', 'sí')} |
| {T('Notebook code, text, tables and numbers = F1', 'Código, texto, tablas y cifras del notebook = F1')} | {analytic_nb} |
| {T('Chart structure (data, titles, labels, legends) = reference', 'Estructura de los gráficos (datos, títulos, etiquetas, leyendas) = referencia')} | {ctx['chart_msg']} |
| {T('Tests', 'Pruebas')} | **{passed} passed, {failed} failed, {xfailed} xfailed, {xpassed} xpassed** |
| {T('show_results.py writes nothing (en, es, --all)', 'show_results.py no escribe nada (en, es, --all)')} | {T('tree identical before and after', 'árbol idéntico antes y después') if ctx['readonly_ok'] else T('FILES CHANGED', 'CAMBIARON ARCHIVOS')} |
| {T('Eight declarative KPIs = F0, F1, F2 and src/metrics.py', 'Ocho KPIs declarativos = F0, F1, F2 y src/metrics.py')} | **{ok8} / 8** |
| {T('47 reference metrics vs F0, direct / canonical route', '47 métricas de referencia frente a F0, ruta directa / canónica')} | **{md47} / 47** · **{mc47} / 47** |
| {T('README results blocks (EN, ES) = computed results', 'Bloques de resultados del README (EN, ES) = resultados calculados')} | {T('identical', 'idénticos') if not ctx['readme_probs'] else '; '.join(ctx['readme_probs'])} |
| {T('Internal links', 'Enlaces internos')} | {ctx['links_checked']} {T('checked', 'comprobados')}, {len(ctx['link_probs'])} {T('broken', 'rotos')} |
| {T('Frozen: baseline/, reports/f1/, reports/f2/, reports/f3/', 'Congelados: baseline/, reports/f1/, reports/f2/, reports/f3/')} | {frozen_line} ({len(ctx['fz_after'])} {T('files', 'archivos')}) |
| {T('Reproducibility', 'Reproducibilidad')} | {chk} |

### {T('Graphical verification (strict, byte for byte)', 'Verificación gráfica (estricta, byte a byte)')}

| {T('Check', 'Comprobación')} | {T('Result', 'Resultado')} |
|---|---|
| {T('Executed notebook = F1 bytes, including the PNG images', 'Notebook ejecutado = bytes de F1, incluidas las imágenes PNG')} | {graph_nb} |
| {T('README figures = notebook outputs', 'Gráficos del README = salidas del notebook')} | {T('identical', 'idénticos') if ctx['fig_ok'] else T('DIFFERENT', 'DISTINTOS')}{T(' (from the versioned reference notebook)', ' (a partir del notebook de referencia versionado)') if (portable and not nbo['identical']) else ''} |
| {T('Rendering environment of this run', 'Entorno de renderizado de esta ejecución')} | {env_lines(ctx['render_env'])} |
| {T('Reference rendering environment (F1 images)', 'Entorno de renderizado de referencia (imágenes de F1)')} | {env_lines(rc.REFERENCE_RENDER_ENVIRONMENT)} |

{T('The cause of a PNG difference is not inferred from these versions: they are recorded so that environments can be compared.', 'La causa de una diferencia en los PNG no se deduce de estas versiones: se registran para poder comparar entornos.')}

## {T('Fixture variants (engine)', 'Variantes del fixture (motor)')}

| {T('Variant', 'Variante')} | {T('available / not available', 'disponibles / no disponibles')} | {T('= hand values and approved matrix', '= valores a mano y matriz aprobada')} |
|---|---|---|
{vrows}

## {T('Security review (patterns)', 'Revisión de seguridad (patrones)')}

{T('Reviewed', 'Revisado')}: {scan['text_files_scanned']} {T('repository text files (all files Git would track, data and notebook included)', 'archivos de texto del repositorio (todo lo que Git versionaría, incluidos datos y notebook)')}; {T('patterns', 'patrones')}: {', '.join(scan['patterns'])}. {T('Notebook', 'Notebook')}: {T('metadata keys', 'claves de metadatos')} {nb['metadata_keys']}, {T('cell metadata', 'metadatos de celda')} {nb['cell_metadata_keys'] or '—'}, {nb['outputs']} {T('outputs', 'salidas')}, {nb['errors']} {T('errors', 'errores')}, {nb['stderr']} stderr, {nb['images']} {T('images', 'imágenes')}. {T('Column names reviewed by value', 'Columnas revisadas por valor')}: {scan['reviewed_columns']}.

{T('Findings', 'Hallazgos')}:

{findings}

{T('Limits: a pattern scan can miss secrets or personal data written in other forms, and does not read images (', 'Límites: un escaneo por patrones puede no detectar secretos o datos personales escritos de otra forma, y no lee imágenes (')}{', '.join(scan['binary_files_not_scanned']) or '—'}{T('). The file holding the patterns is excluded (', '). Se excluye el archivo que contiene los patrones (')}{', '.join(scan['excluded'])}{T('). Ignore rules are applied with a simplified matcher; `git check-ignore` is the authoritative check once a repository exists. This review is not a guarantee of security.', '). Las reglas de exclusión se aplican con un comparador simplificado; `git check-ignore` es la comprobación definitiva cuando exista un repositorio. Esta revisión no garantiza la seguridad.')}

## {T('Files against', 'Archivos frente a')} `{F3_ID}`

{count_txt}. {T('Problems', 'Problemas')}:

{bad}

{T('Modified (declared):', 'Modificados (declarados):')}

{mod}

{T('New (declared):', 'Nuevos (declarados):')}

{new}

{T('Intact (byte-identical to', 'Intactos (idénticos byte a byte a')} `{F3_ID}`; {T('the frozen folders reports/f2/ and reports/f3/ are checked file by file above', 'las carpetas congeladas reports/f2/ y reports/f3/ se comprueban archivo a archivo arriba')}):

{intact}

{T('Per-file hashes:', 'Hashes por archivo:') + (' `reports/release/F3_COMPARISON' + sfx + '.md` ' + T('(strict run)', '(ejecución estricta)') if portable else f' [`F3_COMPARISON{sfx}.md`](F3_COMPARISON{sfx}.md)')}.

## {T('Changes against', 'Cambios frente a')} `{GH0_ID}` (`{GH0_MANIFEST}`, tree id `{GH0_TREE_ID[:16]}…`, {T('pinned, read only', 'fijado, solo lectura')})

{count0_txt}. {T('Modified (declared):', 'Modificados (declarados):')}

{mod0}

{T('New (declared):', 'Nuevos (declarados):')}

{new0}

{T('Every other file is byte-identical to', 'Todos los demás archivos son idénticos byte a byte a')} `{GH0_ID}`.
"""
        (dest / f"{base}{sfx}.md").write_text(report, encoding="utf-8", newline="\n")
        if portable:
            continue
        frow = "\n".join(f"| `{r['file']}` | {r['status']} | `{(r['ref'] or '—')[:16]}` | `{(r['cur'] or '—')[:16]}` | "
                         f"{DECLARED_MODIFIED.get(r['file'], '') if r['status'].startswith('modified') else ''} |" for r in rows)
        comp = f"""{T('**Language:** English | [Español](F3_COMPARISON.es.md)', '**Idioma:** [English](F3_COMPARISON.md) | Español')}

# {VERSION_ID} {T('vs', 'frente a')} {F3_ID}

{T('Reference', 'Referencia')}: `reports/f3/MANIFEST_F3.sha256` (tree id `{F3_TREE_ID}`, {T('not modified', 'no se modifica')}). {count_txt}.

| {T('File', 'Archivo')} | {T('Status', 'Estado')} | SHA-256 {F3_ID} | SHA-256 {VERSION_ID} | {T('Declared change', 'Cambio declarado')} |
|---|---|---|---|---|
{frow}
"""
        (OUT / f"F3_COMPARISON{sfx}.md").write_text(comp, encoding="utf-8", newline="\n")


RESTORABLE = ["data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv", "notebooks/admissions_analysis.ipynb",
              "docs/img/funnel_mature_cohorts.png", "docs/img/main_kpi_by_cohort.png", "docs/img/show_rate_by_month.png"]


def restore(saved: dict[str, bytes], root: Path = ROOT) -> list[str]:
    """Put back the versioned generated files exactly as they were before the run (after a failure, and always at the
    end of a portable run)."""
    restored = []
    for rel, data in saved.items():
        p = Path(root) / rel
        if not p.exists() or p.read_bytes() != data:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            restored.append(rel)
    return restored


def main():
    keep = RESTORABLE + sorted(p.relative_to(ROOT).as_posix() for p in OUT.glob("*") if p.is_file())
    saved = {rel: (ROOT / rel).read_bytes() for rel in keep if (ROOT / rel).exists()}
    try:
        _main(saved)
    except SystemExit as e:
        if e.code not in (None, 0):
            back = restore(saved)
            print("[restore] versioned generated files put back as before the run:", ", ".join(back) or "none needed")
        raise


def _main(saved):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="strict mode: require the stored release manifest")
    ap.add_argument("--mode", choices=["strict", "portable"], default="strict",
                    help="strict (default): the notebook must be byte-identical to F1, PNG images included; "
                         "portable: everything analytical must be identical, PNG differences are reported separately")
    args = ap.parse_args()
    portable = args.mode == "portable"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    stored_path = OUT / "MANIFEST_RELEASE.sha256"
    stored = stored_path.read_text(encoding="utf-8") if stored_path.exists() else None
    check = args.check or portable                      # portable mode always compares with the stored manifest
    if check and stored is None:
        raise SystemExit("no stored reports/release/MANIFEST_RELEASE.sha256 to check against")
    print(f"[mode] {args.mode}" + (" — analytical verification; PNG differences reported separately, not a byte-for-byte reproduction"
                                    if portable else " — analytical and byte-for-byte graphical verification"))
    env, env_diffs = F3.environment()
    print("[environment]", "matches baseline/environment.txt" if not env_diffs else f"DIFFERS: {env_diffs}")
    render_env = rc.render_environment()
    print("[rendering]", ", ".join(f"{k} {v}" for k, v in render_env.items()))
    fz_before = frozen_hashes()
    probs = frozen_problems(fz_before)
    if probs:
        raise SystemExit("frozen references differ before the run: " + "; ".join(probs))
    print(f"[frozen] F0, F1, F2 and F3 verified ({len(fz_before)} files)")

    f1 = manifest_text((ROOT / "reports" / "f1" / "MANIFEST_F1.sha256").read_text(encoding="utf-8"))
    f1_nb = f1["notebooks/admissions_analysis.ipynb"]
    nb_path = ROOT / "notebooks" / "admissions_analysis.ipynb"
    nb_reference_bytes = nb_path.read_bytes() if nb_path.exists() and sha(nb_path) == f1_nb else None
    if portable and nb_reference_bytes is None:
        raise SystemExit("portable mode needs the versioned reference notebook (F1 bytes) before the run")
    nb_reference = json.loads(nb_reference_bytes.decode("utf-8")) if nb_reference_bytes else None
    log = []
    clean(log, keep_release_reports=portable)
    run("generate", [sys.executable, "src/generate_data.py"], log)
    f0 = manifest_text((ROOT / "baseline" / "MANIFEST.sha256").read_text(encoding="utf-8"))
    bad = [p for p in ("data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv") if sha(ROOT / p) != f0[p]]
    if bad:
        raise SystemExit(f"generated data differ from F0: {bad}")
    run("notebook", [sys.executable, "scripts/build_notebook.py"], log)   # exits 1 if any cell raised an error
    rebuilt_bytes = nb_path.read_bytes()
    nb_rebuilt_sha = hashlib.sha256(rebuilt_bytes).hexdigest()
    if nb_reference_bytes is not None:
        nb_outcome = rc.notebook_outcome(args.mode, rebuilt_bytes, nb_reference_bytes)
    else:                                             # strict without a reference copy: compare with the F1 hash only
        same = nb_rebuilt_sha == f1_nb
        nb_outcome = {"ok": same, "identical": same, "png": [], "other": [] if same else ["no reference copy to compare"]}
    if not portable:
        nb_diag = notebook_diagnosis(f1_nb, nb_reference)
        print("[notebook]", nb_diag)
        if not nb_outcome["identical"]:
            raise SystemExit("executed notebook differs from F1 (strict mode): " + nb_diag)
    else:
        if not nb_outcome["ok"]:
            print("[notebook] ANALYTICAL DIFFERENCE:", "; ".join(nb_outcome["other"][:10]))
            raise SystemExit("executed notebook differs from F1 beyond the PNG images: " + "; ".join(nb_outcome["other"][:10]))
        if nb_outcome["identical"]:
            print("[notebook] identical to F1, PNG images included")
        else:
            nb_path.write_bytes(nb_reference_bytes)   # never keep this machine's rendering in the versioned notebook
            print(f"[notebook] analytical content identical to F1; {len(nb_outcome['png'])} PNG image(s) differ "
                  f"(rebuilt {nb_rebuilt_sha[:16]}…, reference {f1_nb[:16]}…) — graphical difference reported separately; "
                  "versioned notebook kept")
    chart_out = run("chart structure", [sys.executable, "scripts/chart_signature.py", "--check"], log, check=False)
    chart_ok = log[-1]["exit"] == 0
    chart_msg = chart_out.strip().splitlines()[-1] if chart_out.strip() else "no output"
    print("[charts]", chart_msg)
    if not chart_ok:
        raise SystemExit("chart structure differs from the reference: " + chart_msg)
    run("figures", [sys.executable, "scripts/export_figures.py"], log)
    run("map", [sys.executable, "scripts/map_to_canonical.py"], log)
    tests_out = run("tests", [sys.executable, "-m", "pytest", "-q"], log)
    if F3.parse_pytest(tests_out)[2] or F3.parse_pytest(tests_out)[3]:
        raise SystemExit("xfail / xpass found: every test must pass normally")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)

    before = tree_snapshot()
    for extra in ([], ["--lang", "es"], ["--all"]):
        run("show_results" + ("" if not extra else " " + " ".join(extra)), [sys.executable, "scripts/show_results.py", *extra], log)
    readonly_ok = tree_snapshot() == before
    print("[read-only] show_results.py wrote nothing:", readonly_ok)

    R = F3.reconcile()
    res = rc.load_results()
    readme_probs = rc.readme_problems(res)
    link_probs, links_checked = rc.link_problems()
    fig_ok = run("figures --check", [sys.executable, "scripts/export_figures.py", "--check"], log, check=False).endswith("identical to the notebook outputs")
    scan = rc.security_scan()
    print(f"[documents] README blocks ok: {not readme_probs} · links: {links_checked} checked, {len(link_probs)} broken · figures ok: {fig_ok}")
    print(f"[security] {scan['text_files_scanned']} text files scanned · findings: {len(scan['findings'])}")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)

    rows, problems = classify(manifest_text((ROOT / "reports" / "f3" / "MANIFEST_F3.sha256").read_text(encoding="utf-8")))
    rows0, problems0 = classify(manifest_text((ROOT / GH0_MANIFEST).read_text(encoding="utf-8")),
                                DECLARED_MODIFIED_VS_GH0, DECLARED_NEW_VS_GH0)
    problems += [f"vs {GH0_ID}: {x}" for x in problems0]
    fz_after = frozen_hashes()
    fz_probs = frozen_problems(fz_after)
    text, tree_id = release_manifest()
    check_result = None
    if check:
        old, new = manifest_text(stored), manifest_text(text)
        diff = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        check_result = ({"en": f"identical to the stored release manifest ({len(new)} files) — tree id {tree_id[:16]}",
                         "es": f"idéntico al manifiesto guardado ({len(new)} archivos) — tree id {tree_id[:16]}"}
                        if not diff else {"en": "DRIFT in: " + ", ".join(diff), "es": "DIFERENCIAS en: " + ", ".join(diff)})
        print("[check]", check_result["en"])
    if not portable:                                   # portable mode never writes reports/release/
        OUT.mkdir(parents=True, exist_ok=True)
        stored_path.write_text(stored if args.check else text, encoding="utf-8", newline="\n")
    ok8 = all(all(r[k] for k in ("f0", "f1", "f2", "metrics_py")) for r in R["rows"])
    okv = all(v["counts_as_planned"] and not v["mismatches"] for v in R["variants"].values())
    ok47 = R["direct_identical"] and bool(R["rec_direct"].match.astype(bool).all()) and bool(R["rec_canon"].match.astype(bool).all())
    analytic_ok = not (problems or fz_before != fz_after or fz_probs or not (ok8 and okv and ok47 and readonly_ok and fig_ok and chart_ok)
                       or readme_probs or link_probs or scan["findings"] or (check_result and check_result["en"].startswith("DRIFT"))
                       or not nb_outcome["ok"])
    import platform
    write_reports({"log": log, "rows": rows, "rows0": rows0, "R": R, "scan": scan, "env": env, "env_diffs": env_diffs, "tree_id": tree_id,
                   "check_result": check_result, "fz_before": fz_before, "fz_after": fz_after, "fz_probs": fz_probs,
                   "nb_diag": "identical" if nb_outcome["identical"] else "different", "fig_ok": fig_ok, "readonly_ok": readonly_ok,
                   "readme_probs": readme_probs, "link_probs": link_probs, "links_checked": links_checked,
                   "platform": f"{platform.system()} {platform.machine()} · Python {platform.python_version()}",
                   "mode": args.mode, "nb_outcome": nb_outcome, "nb_rebuilt_sha": nb_rebuilt_sha, "nb_reference_sha": f1_nb,
                   "chart_msg": chart_msg, "render_env": render_env, "analytic_ok": analytic_ok})
    if portable:
        PORTABLE_OUT.mkdir(parents=True, exist_ok=True)
        (PORTABLE_OUT / "portable_result.json").write_text(json.dumps({
            "version_id": VERSION_ID, "mode": "portable", "analytical_verification": "passed" if analytic_ok else "not passed",
            "strict_graphical_verification": "passed" if nb_outcome["identical"] else "not passed",
            "png_differences": nb_outcome["png"], "rebuilt_notebook_sha256": nb_rebuilt_sha, "reference_notebook_sha256": f1_nb,
            "rendering_environment": render_env, "reference_rendering_environment": rc.REFERENCE_RENDER_ENVIRONMENT},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        back = restore(saved)                          # the versioned files stay exactly as before the run
        print("[restore] versioned generated files:", ", ".join(back) or "unchanged")
        print(f"[report] {(PORTABLE_OUT / 'PORTABLE_REPORT.md').relative_to(ROOT).as_posix()} (outside the reference manifests)")
    for d in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(d)
    missing_outputs = [] if portable else sorted(r for r in REPORT_FILES if not (ROOT / r).exists())
    if missing_outputs:
        print("[outputs] MISSING:", missing_outputs)
    print(f"[compare] vs {F3_ID}: {problems or 'no problems'} · frozen unchanged: {fz_before == fz_after and not fz_probs}")
    print(f"[kpis] 8 declarative = F0/F1/F2/metrics.py: {ok8} · 47 metrics ok: {ok47} · variants ok: {okv}")
    print(f"[result] analytical verification: {'PASSED' if analytic_ok else 'NOT PASSED'} · strict graphical verification: "
          + ("PASSED" if nb_outcome["identical"] else ("NOT PASSED (PNG images differ; reported separately)" if portable else "NOT PASSED")))
    print(f"{VERSION_ID} · tree id {tree_id}")
    if not analytic_ok or missing_outputs or (not portable and not nb_outcome["identical"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
