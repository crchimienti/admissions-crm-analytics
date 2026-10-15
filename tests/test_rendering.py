"""Reference chart rendering (v1.4.1-gh): bundled fonts, licence, explicit settings, no silent fallback.

Renderizado de referencia de los gráficos: fuentes incluidas, licencia, ajustes explícitos, sin sustitución silenciosa.

The end-to-end check (the rebuilt notebook equals the F1 bytes) is a step of scripts/release_run.py, which rebuilds the
notebook from scratch; these tests check the pieces quickly.
"""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys

import pytest

from kpi_helpers import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import notebook_rendering as nr  # noqa: E402

FONT_DIR = ROOT / "assets" / "fonts" / "inter"
OFL_SHA256 = "262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a"


def test_font_files_are_the_pinned_ones():
    for name, digest in nr.FONTS.items():
        assert hashlib.sha256((FONT_DIR / name).read_bytes()).hexdigest() == digest, name
    assert sorted(nr.FONTS) == ["Inter-Bold.otf", "Inter-Regular.otf"]
    assert nr.check_files() == [FONT_DIR / "Inter-Regular.otf", FONT_DIR / "Inter-Bold.otf"]


def test_licence_copyright_and_provenance_are_shipped():
    ofl = (FONT_DIR / "OFL.txt").read_text(encoding="utf-8")
    # the upstream LICENSE.txt of Inter at tag v4.0, unchanged
    assert hashlib.sha256((FONT_DIR / "OFL.txt").read_bytes()).hexdigest() == OFL_SHA256
    assert "SIL OPEN FONT LICENSE Version 1.1" in ofl and "Copyright (c) 2016 The Inter Project Authors" in ofl
    assert "PERMISSION AND CONDITIONS" in ofl and "DISCLAIMER" in ofl
    prov = (FONT_DIR / "FONTS.md").read_text(encoding="utf-8")
    for name, digest in nr.FONTS.items():
        assert name in prov and digest in prov, name
    for fact in ("4.0+ds-1", "Version 4.000;git-a52131595", "https://github.com/rsms/inter", "SIL Open Font License", OFL_SHA256):
        assert fact in prov, fact


def test_configure_uses_the_project_files_and_explicit_settings():
    code = ("import sys; sys.path.insert(0, 'scripts'); import notebook_rendering as nr; import matplotlib as mpl\n"
            "mpl.rcParams['font.family'] = ['DejaVu Sans']; mpl.rcParams['text.hinting'] = 'default'\n"
            "print(nr.configure())\n")
    p = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    out = p.stdout.strip()
    assert "'normal': 'Inter-Regular.otf'" in out and "'bold': 'Inter-Bold.otf'" in out
    assert "'text.hinting': 'no_hinting'" in out and "['Inter', 'sans-serif', 'DejaVu Sans']" in out


def test_another_inter_on_the_system_is_never_used(tmp_path):
    """A different file registered as "Inter" (here: a copy of DejaVu Sans renamed by matplotlib's entry) is dropped."""
    code = ("import sys, dataclasses; sys.path.insert(0, 'scripts'); import notebook_rendering as nr\n"
            "from matplotlib import font_manager as fm\n"
            "dv = next(f for f in fm.fontManager.ttflist if f.name == 'DejaVu Sans' and f.weight == 400 and f.style == 'normal')\n"
            "fm.fontManager.ttflist.insert(0, dataclasses.replace(dv, name='Inter'))\n"
            "print(nr.configure()['fonts'])\n")
    p = subprocess.run([sys.executable, "-B", "-c", code], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "{'normal': 'Inter-Regular.otf', 'bold': 'Inter-Bold.otf'}"


@pytest.mark.parametrize("problem", ["missing", "changed"])
def test_missing_or_changed_font_stops_with_an_error(tmp_path, monkeypatch, problem):
    for name in nr.FONTS:
        (tmp_path / name).write_bytes((FONT_DIR / name).read_bytes())
    if problem == "missing":
        (tmp_path / "Inter-Bold.otf").unlink()
    else:
        (tmp_path / "Inter-Bold.otf").write_bytes(b"not the pinned font")
    monkeypatch.setattr(nr, "FONT_DIR", tmp_path)
    monkeypatch.setattr(nr, "ROOT", tmp_path.parent)
    with pytest.raises(nr.RenderingError):
        nr.check_files()


def test_build_notebook_applies_the_rendering_without_changing_cells():
    src = (ROOT / "scripts" / "build_notebook.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    execute = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "execute")
    body = ast.unparse(execute)
    assert "notebook_rendering.check_files()" in body
    assert "--IPKernelApp.exec_lines=" in body and "notebook_rendering.kernel_exec_line()" in body
    assert "notebook_rendering" not in "".join(ast.unparse(n) for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == "execute"))
    line = nr.kernel_exec_line()
    assert "\n" not in line and "kernel_setup()" in line and "MATPLOTLIBRC" not in line
    assert "MATPLOTLIBRC" not in (ROOT / "scripts" / "notebook_rendering.py").read_text(encoding="utf-8").split('"""', 2)[2]
