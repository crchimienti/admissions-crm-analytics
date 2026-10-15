"""Serialization (v1.4.0-gh): files written on any operating system have the same bytes as the frozen references.

Serialización: los archivos escritos en cualquier sistema operativo tienen los mismos bytes que las referencias.

* The generator writes LF line endings even when the platform line separator is CRLF (simulated by patching
  os.linesep, which pandas reads at call time): the three CSV files equal the F0 manifest byte for byte.
* Every CSV write sets lineterminator="\\n"; every text write of the scripts that run on this tree sets newline="\\n"
  (or writes bytes); the notebook is written through a file opened with newline="\\n".
* No versioned text file contains a carriage return, and .gitattributes turns off end-of-line conversion.
"""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys

import pytest

from kpi_helpers import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import release_checks as rc  # noqa: E402

CSV = ("leads.csv", "activities.csv", "dq_ground_truth.csv")
ACTIVE_SCRIPTS = ["scripts/build_notebook.py", "scripts/release_run.py", "scripts/export_figures.py",
                  "scripts/show_results.py", "scripts/release_checks.py", "scripts/map_to_canonical.py"]


def f0_manifest():
    rows = (ROOT / "baseline" / "MANIFEST.sha256").read_text(encoding="utf-8").strip().splitlines()
    return {p: h for h, p in (r.split("  ", 1) for r in rows)}


@pytest.mark.parametrize("linesep", ["\n", "\r\n"])
def test_generator_bytes_equal_f0_with_any_line_separator(tmp_path, linesep):
    code = ("import os, runpy, sys\n"
            f"os.linesep = {linesep!r}\n"
            f"sys.argv = ['generate_data.py', '--out', {str(tmp_path)!r}]\n"
            f"runpy.run_path({str(ROOT / 'src' / 'generate_data.py')!r}, run_name='__main__')\n")
    p = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    man = f0_manifest()
    for name in CSV:
        data = (tmp_path / name).read_bytes()
        assert b"\r" not in data, name
        assert hashlib.sha256(data).hexdigest() == man[f"data/{name}"], name


def _calls(path):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]


def _kw(call, name):
    return next((k.value for k in call.keywords if k.arg == name), None)


def test_every_csv_write_sets_lf():
    for path in ("src/generate_data.py", "src/canonical/contract.py"):
        calls = [c for c in _calls(path) if isinstance(c.func, ast.Attribute) and c.func.attr == "to_csv"]
        assert calls, path
        for c in calls:
            v = _kw(c, "lineterminator")
            assert isinstance(v, ast.Constant) and v.value == "\n", (path, c.lineno)


def test_every_csv_write_in_the_tests_sets_lf():
    """v1.4.2-gh: temporary CSV files written by tests are compared byte for byte with LF references, so they must be
    written with LF too (test_regeneration_is_reproducible wrote CRLF on Windows)."""
    found = 0
    for p in sorted((ROOT / "tests").glob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        for c in _calls(rel):
            if isinstance(c.func, ast.Attribute) and c.func.attr == "to_csv":
                v = _kw(c, "lineterminator")
                assert isinstance(v, ast.Constant) and v.value == "\n", (rel, c.lineno)
                found += 1
    assert found >= 1


def test_every_text_write_of_the_active_scripts_sets_lf():
    for path in ACTIVE_SCRIPTS:
        for c in _calls(path):
            if isinstance(c.func, ast.Attribute) and c.func.attr == "write_text":
                v = _kw(c, "newline")
                assert isinstance(v, ast.Constant) and v.value == "\n", (path, c.lineno)
            if isinstance(c.func, ast.Name) and c.func.id == "open":
                mode = c.args[1].value if len(c.args) > 1 and isinstance(c.args[1], ast.Constant) else _kw(c, "mode")
                mode = mode.value if isinstance(mode, ast.Constant) else mode
                if isinstance(mode, str) and ("w" in mode or "a" in mode) and "b" not in mode:
                    v = _kw(c, "newline")
                    assert isinstance(v, ast.Constant) and v.value == "\n", (path, c.lineno)


def test_notebook_is_written_through_an_lf_file():
    calls = [c for c in _calls("scripts/build_notebook.py") if isinstance(c.func, ast.Attribute) and c.func.attr == "write"
             and isinstance(c.func.value, ast.Name) and c.func.value.id == "nbf"]
    assert len(calls) == 1
    target = calls[0].args[1]
    assert isinstance(target, ast.Name) and target.id == "fh", "nbformat must write to the LF file handle, not to a path"


def test_versioned_text_files_have_no_carriage_return():
    text_files = [(rel, p.read_bytes()) for rel, p in rc.repo_files() if not rc.is_binary(rel, p.read_bytes())]
    bad = [rel for rel, data in text_files if b"\r" in data]
    assert not bad, bad
    assert len(text_files) > 150


def test_gitattributes_turns_off_eol_conversion():
    rules = [l.strip() for l in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    assert rules == ["* -text"]
