"""GitHub preparation (v1.4.0-gh): environment files, ignore rules, README, figures, read-only quick start, security
scan, workflow and declared changes.

Preparación para GitHub: archivos de entorno, reglas de exclusión, README, gráficos, inicio rápido de solo lectura,
escaneo de seguridad, workflow y cambios declarados.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys

import pytest
import yaml

from kpi_helpers import ROOT
from release_declared import GH_DECLARED_MODIFIED, GH_PINNED

sys.path.insert(0, str(ROOT / "scripts"))
import export_figures  # noqa: E402
import release_checks as rc  # noqa: E402

VERSION_IDS = ["v1.0.0-f0", "v1.1.0-f1", "v1.2.0-f2", "v1.2.1-f2", "v1.2.2-f2", "v1.2.3-f2", "v1.3.0-f3", "v1.3.1-f3", "v1.4.0-gh", "v1.4.1-gh", "v1.4.2-gh", "v1.4.3-gh", "v1.4.4-gh", "v1.5.0-app", "v1.5.1-app"]


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def results():
    return rc.load_results()


# ----- environment ------------------------------------------------------------ #
def lock_lines():
    return [l for l in (ROOT / "requirements-lock.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def test_lock_pins_every_package_and_matches_the_reference_environment():
    pins = {}
    for line in lock_lines():
        req = line.split("#")[0].split(";")[0].strip()
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+", req), line       # exact pin, no URL or local file reference
        name, version = req.split("==")
        pins[name.lower().replace("_", "-")] = version
    env = dict(l.split("==", 1) for l in (ROOT / "baseline" / "environment.txt").read_text(encoding="utf-8").split())
    for pkg, version in env.items():
        if pkg != "python":
            assert pins[pkg.lower()] == version, pkg
    reference = [l for l in lock_lines() if l.endswith("# reference")]
    assert len(reference) == len(env) - 1
    assert "pip" not in pins and "streamlit" not in pins                            # app dependencies stay separate


def test_lock_marks_platform_only_dependencies():
    marked = {l.split("==")[0].lower(): l.split(";", 1)[1].split("#")[0].strip() for l in lock_lines() if ";" in l}
    assert marked == {"appnope": 'platform_system == "Darwin"', "colorama": 'sys_platform == "win32"',
                      "pexpect": 'sys_platform != "win32"', "ptyprocess": 'sys_platform != "win32"',
                      "tzdata": 'sys_platform == "win32"'}


def test_requirements_txt_unchanged_since_f0():
    man = {p: h for h, p in (l.split("  ", 1) for l in (ROOT / "baseline/MANIFEST.sha256").read_text(encoding="utf-8").splitlines())}
    assert sha("requirements.txt") == man["requirements.txt"]


# ----- what Git would track ----------------------------------------------------- #
def test_gitignore_keeps_the_original_rules_and_covers_local_files():
    pats = rc.ignore_patterns()
    assert pats[:4] == ["__pycache__/", ".pytest_cache/", ".ipynb_checkpoints/", "*.pyc"]
    for rel in (".venv/lib/x.py", "venv/x", "env/x", ".env", ".env.local", "copy-v1.zip", "F3.diff", "build/canonical/x.csv",
                ".DS_Store", "Thumbs.db", ".streamlit/secrets.toml", "src/__pycache__/m.pyc", ".idea/x", ".vscode/x", "run.log"):
        assert rc.is_ignored(rel, pats), rel


def test_files_the_tests_need_are_not_ignored():
    pats = rc.ignore_patterns()
    for rel in ("data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv", "notebooks/admissions_analysis.ipynb",
                "tests/fixtures/canonical_handcalc/expected.json", "baseline/MANIFEST.sha256", "reports/f1/MANIFEST_F1.sha256",
                "reports/f2/MANIFEST_F2.sha256", "reports/f3/MANIFEST_F3.sha256", "docs/img/funnel_mature_cohorts.png",
                "requirements-lock.txt", ".gitattributes", ".github/workflows/tests.yml", "scripts/build_notebook.py"):
        assert (ROOT / rel).exists() and not rc.is_ignored(rel, pats), rel


def test_repository_top_level_is_the_project_only():
    top = {rel.split("/")[0] for rel, _ in rc.repo_files()}
    assert top == {".gitattributes", ".gitignore", ".github", ".streamlit", "CHANGELOG.md", "app", "LICENSE", "LICENSE-CONTENT", "README.md", "README.es.md", "assets", "baseline",
                   "config", "data", "docs", "notebooks", "profiles", "reports", "requirements.txt",
                   "requirements-lock.txt", "requirements-app.txt", "schema", "scripts", "src", "tests"}


# ----- README, figures and documents ------------------------------------------- #
def test_readme_results_blocks_equal_the_computed_results(results):
    assert rc.readme_problems(results) == []
    assert all(r.get("equals_metrics_py") for r in results["eight"])
    assert results["metrics_equal_f0"] == results["metrics_total"] == 47


@pytest.mark.parametrize("name,phrases", [
    ("README.md", ["**47** computed by the reference engine", "only **8** configured in the declarative engine",
                   "**100 % synthetic**", "only the **admissions** profile is tested", "**not connected** to any CRM",
                   "**UTC is not supported yet**", "Future phases", "not implemented", "prepared, not yet verified"]),
    ("README.es.md", ["**47** calculadas por el motor de referencia", "solo **8** configuradas en el motor declarativo",
                      "**100 % sintéticos**", "solo está probado el perfil de **admisiones**", "**sin conexión** a ningún CRM",
                      "**UTC todavía no está soportado**", "Fases futuras", "no implementadas", "preparado, pendiente de verificar"]),
])
def test_readme_states_the_scope(name, phrases):
    text = (ROOT / name).read_text(encoding="utf-8")
    for ph in phrases:
        assert ph in text, (name, ph)
    intro = text.split("## Main synthetic results")[0] if name == "README.md" else text.split("## Principales resultados")[0]
    assert "tree id" not in intro and "MANIFEST" not in intro                     # phases and hashes stay out of the intro


def test_internal_links_resolve():
    problems, checked = rc.link_problems()
    assert not problems and checked > 30, problems


def test_readme_figures_are_the_notebook_outputs():
    figures = export_figures.extract()
    for name, data in figures.items():
        assert (ROOT / "docs" / "img" / name).read_bytes() == data, name
        for readme in ("README.md", "README.es.md"):
            assert f"docs/img/{name}" in (ROOT / readme).read_text(encoding="utf-8"), (readme, name)


def test_changelog_lists_every_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for vid in VERSION_IDS:
        assert f"`{vid}`" in text, vid
    assert "f1a73209cfaf24d3768784e121f376e1d0ec485eca31ddd22f2b57e09ef23c34" in text


def test_licence_is_pending_until_chosen():
    if not (ROOT / "LICENSE").exists():
        assert "not chosen yet" in (ROOT / "README.md").read_text(encoding="utf-8")
        assert "todavía no elegida" in (ROOT / "README.es.md").read_text(encoding="utf-8")


# ----- quick start ------------------------------------------------------------ #
def snapshot():
    return {p.relative_to(ROOT).as_posix(): (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir")
            for p in sorted(ROOT.rglob("*")) if ".pytest_cache" not in p.parts}


@pytest.mark.parametrize("args", [[], ["--lang", "es", "--all"]])
def test_show_results_is_read_only(args):
    before = snapshot()
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "show_results.py"), *args], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    assert snapshot() == before
    out = p.stdout
    assert ("Synthetic data" in out) if not args else ("Datos sintéticos" in out)
    assert "8/8" in out and "47/47" in out


# ----- security ---------------------------------------------------------------- #
def test_security_scan_finds_nothing():
    scan = rc.security_scan()
    assert scan["findings"] == [], scan["findings"]
    assert scan["text_files_scanned"] > 100
    assert scan["notebook"]["metadata_keys"] == ["kernelspec", "language_info"]


def test_security_scan_detects_planted_values(tmp_path, monkeypatch):
    """The patterns do fire: planted fake values in a temporary copy of the file list are reported."""
    fake = tmp_path / "planted.md"
    fake.write_text("contact: " + "someone" + "@" + "example.org\npath " + "/ho" + "me/someone/x\n"
                    + "api_key = " + "'abcdefghij'\n", encoding="utf-8", newline="\n")
    monkeypatch.setattr(rc, "repo_files", lambda: iter([("planted.md", fake)]))
    kinds = {f["kind"] for f in rc.security_scan()["findings"]}
    assert {"email address", "local absolute path", "credential assignment"} <= kinds


# ----- workflow and declared changes ------------------------------------------- #
def test_workflow_runs_tests_on_three_systems_with_the_lock():
    text = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    wf = yaml.safe_load(text)
    jobs = wf["jobs"]
    assert jobs["tests"]["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest", "macos-latest"]
    steps = " ".join(str(s) for s in jobs["tests"]["steps"])
    assert "requirements-lock.txt" in steps and "pytest -q" in steps and "show_results.py" in steps and "3.13.16" in steps
    for job in ("reproduction-portable", "reproduction-strict"):          # v1.4.3-gh: the two levels are separate jobs
        assert jobs[job]["if"] == "github.event_name == 'workflow_dispatch'", job
    assert jobs["reproduction-portable"]["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest", "macos-latest"]
    assert "--mode portable" in str(jobs["reproduction-portable"]["steps"])
    assert jobs["reproduction-strict"]["runs-on"] == "ubuntu-latest" and "--mode portable" not in str(jobs["reproduction-strict"]["steps"])
    assert wf["permissions"] == {"contents": "read"} and "secrets." not in text


def test_declared_changes_are_consistent():
    import release_run
    assert set(GH_DECLARED_MODIFIED) == set(release_run.DECLARED_MODIFIED)
    for rel, (_old, new, _why) in GH_PINNED.items():
        assert sha(rel) == new, rel
    for rel in release_run.DECLARED_NEW:
        assert (ROOT / rel).exists(), rel


# ----- v1.4.1-gh: README results block, wording and reproducibility claims ------------------------------- #
def _block(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    assert text.count(rc.RESULTS_START) == 1 and text.count(rc.RESULTS_END) == 1, name
    return text.split(rc.RESULTS_START, 1)[1].split(rc.RESULTS_END, 1)[0]


def _rows(block):
    return [[c.strip() for c in line.strip().strip("|").split("|")] for line in block.splitlines()
            if line.startswith("| ") and not line.startswith(("| KPI |", "| Metric |", "| Métrica |"))]


@pytest.mark.parametrize("name,lang", [("README.md", "en"), ("README.es.md", "es")])
def test_results_block_is_not_empty_and_lists_the_eight_kpis(name, lang, results):
    block = _block(name)
    assert block.startswith("\n\n") and block.endswith("\n\n")               # blank lines around both markers
    rows = _rows(block)
    labels = [r[0] for r in rows]
    for kpi in results["eight"]:
        assert kpi["label_en" if lang == "en" else "label_es"] in labels, kpi["id"]
    assert len(rows) == 8 + len(rc.REFERENCE_IDS) + 1


def test_results_block_has_the_same_figures_in_both_languages(results):
    def norm(value):   # Spanish 7.691 / 69,9 % / 2.522 € -> English 7,691 / 69.9 % / €2,522
        v = value.replace("días", "days")
        if v.endswith(" €"):
            v = "€" + v[:-2]
        return v.replace(".", "#").replace(",", ".").replace("#", ",")
    en = [r[1] for r in _rows(_block("README.md"))]
    es = [norm(r[1]) for r in _rows(_block("README.es.md"))]
    assert en == es
    computed = [rc.fmt_value(k, "en") for k in results["eight"]]
    assert en[:8] == computed


def test_readme_names_the_exact_intervention_and_its_zero_effect():
    en, es = (ROOT / "README.md").read_text(encoding="utf-8"), (ROOT / "README.es.md").read_text(encoding="utf-8")
    assert "introduction of the personalised WhatsApp" in en and "**zero effect**" in en and "channel change" not in en
    assert "introducción del WhatsApp personalizado" in es and "**efecto cero**" in es and "cambio de canal" not in es


def test_readme_does_not_overstate_reproducibility():
    en, es = (ROOT / "README.md").read_text(encoding="utf-8"), (ROOT / "README.es.md").read_text(encoding="utf-8")
    for text, banned in ((en, ["on every system", "on any system"]), (es, ["en cualquier sistema", "en todos los sistemas"])):
        for phrase in banned:
            assert phrase not in text, phrase
        assert "MATPLOTLIBRC" not in text and "fonts-inter" not in text                 # nothing to configure by hand
    for level in ("| Figures |", "| Data files |", "| Chart rendering |"):
        assert level in en, level
    for level in ("| Cifras |", "| Archivos de datos |", "| Renderizado de gráficos |"):
        assert level in es, level
    assert en.count("pending") >= 3 and es.count("pendiente") >= 3
