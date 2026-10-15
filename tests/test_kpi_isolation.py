"""The F3.0 engine is independent of src/metrics.py and adds no dependency, network or CRM code.

El motor de F3.0 no depende de src/metrics.py y no añade dependencias, red ni código de CRM.
"""
from __future__ import annotations

import ast

from kpi_helpers import ROOT

import subprocess
import sys

ALLOWED = {"__future__", "re", "copy", "dataclasses", "pathlib", "numpy", "pandas", "yaml", "kpispec", "canonical", "src"}


def _imports(path):
    mods = set()
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module)
    return mods


def test_engine_does_not_import_metrics_or_network():
    files = sorted((ROOT / "src" / "kpispec").glob("*.py"))
    assert [p.name for p in files] == ["__init__.py", "engine.py", "fields.py", "spec.py"]
    for p in files:
        mods = _imports(p)
        tops = {m.split(".")[0] for m in mods}
        assert "metrics" not in tops and not any(m.endswith(".metrics") or m == "src.metrics" for m in mods), (p.name, mods)
        assert tops <= ALLOWED, (p.name, tops - ALLOWED)


def test_f3_scripts_have_no_network_or_crm_imports():
    forbidden = {"requests", "urllib", "http", "socket", "httpx", "aiohttp", "hubspot", "simple_salesforce", "streamlit"}
    for rel in ("scripts/f3_run.py",):
        tops = {m.split(".")[0] for m in _imports(ROOT / rel)}
        assert not tops & forbidden, (rel, tops & forbidden)


def test_engine_does_not_load_metrics_or_the_generator_even_indirectly():
    """Run the engine on the fixture in a fresh interpreter: src/metrics.py and the generator are never loaded."""
    code = (
        "import sys; sys.path.insert(0, 'src')\n"
        "from canonical.adapters import admissions as ad\n"
        "from kpispec import engine\n"
        "from kpispec.spec import load_spec\n"
        "res = engine.evaluate(load_spec('profiles/admissions/kpis.yaml'), ad.load('tests/fixtures/canonical_handcalc/v_full'))\n"
        "assert len(res) == 8\n"
        "print(sorted(m for m in ('metrics', 'src.metrics', 'generate_data', 'src.generate_data', 'checks') if m in sys.modules))\n")
    p = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "[]", p.stdout


def test_engine_code_runs_no_subprocess_and_calls_no_generator():
    for p in sorted((ROOT / "src" / "kpispec").glob("*.py")):
        tops = {m.split(".")[0] for m in _imports(p)}
        assert not tops & {"subprocess", "os", "generate_data", "checks"}, (p.name, tops)


def test_engine_tests_do_not_import_metrics():
    for rel in ("tests/kpi_helpers.py", "tests/test_kpi_handcalc.py", "tests/test_kpi_engine_ops.py", "tests/test_kpi_spec_schema.py"):
        tops = {m.split(".")[0] for m in _imports(ROOT / rel)}
        assert "metrics" not in tops, rel
