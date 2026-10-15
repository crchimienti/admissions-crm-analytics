"""F3.0 regression against the frozen F2 reference (v1.2.3-f2).

Regresión de F3.0 contra la referencia congelada de F2 (v1.2.3-f2).

* reports/f2/ is byte-identical to the v1.2.3-f2 delivery (pinned hashes; its manifest's SHA-256 is the F2 tree id).
* Every file of the F2 manifest is unchanged, except the files F3.0 declares as modified.
* scripts/f2_run.py refuses to run on this tree before touching any file.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import PurePath, PurePosixPath, PureWindowsPath

import pytest

from kpi_helpers import ROOT
from release_declared import GH_DECLARED_MODIFIED, GH_PINNED

F2_TREE_ID = "a1df9fca9a38538f912fadfb437b4831f609962baa7b97fe763f68ec7a0885db"
F2_REPORTS = {
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
F3_DECLARED_MODIFIED = {
    "README.md": "F3.0 section, structure and how to run (no figure changed)",
    "README.es.md": "sección F3.0, estructura y cómo ejecutar (ninguna cifra cambia)",
    "docs/PROJECT_STATUS.md": "F3.0 state, F3.5 in the roadmap, FLD reason, frozen F2",
    "docs/PROJECT_STATUS.es.md": "estado de F3.0, F3.5 en la hoja de ruta, motivo FLD, F2 congelada",
    "scripts/f2_run.py": "guard only: refuses to run on the F3 tree (reports/f2/ is frozen)",
    "src/canonical/adapters/admissions.py": "first_human_attempt extracted as a reusable profile function; metrics imported lazily (same results)",
}


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def manifest_rel(path: PurePath, root: PurePath) -> str:
    """A file's path as written in the manifests: relative to the project root, with "/" separators on every system
    (v1.4.1-gh: the earlier check compared Path.as_posix() with str(Path), which differ on Windows)."""
    return path.relative_to(root).as_posix()


def test_reports_f2_frozen():
    for rel, h in F2_REPORTS.items():
        assert sha(rel) == h, rel
    present = sorted(manifest_rel(p, ROOT) for p in (ROOT / "reports" / "f2").iterdir())
    assert present == sorted(F2_REPORTS)                       # exact file list, same pinned hashes as before


@pytest.mark.parametrize("root,path", [
    (PureWindowsPath(r"D:\work\project"), PureWindowsPath(r"D:\work\project\reports\f2\F2_REPORT.md")),
    (PurePosixPath("/srv/project"), PurePosixPath("/srv/project/reports/f2/F2_REPORT.md")),
])
def test_manifest_paths_do_not_depend_on_the_separator(root, path):
    """Separator handling only (pure paths): the same file gives the same manifest key with Windows or POSIX paths,
    while the old comparison (as_posix() against str()) fails for the Windows form. This does not replace running the
    whole test suite on Windows."""
    assert manifest_rel(path, root) == "reports/f2/F2_REPORT.md"
    old_ok = path.as_posix() == str(root / "reports/f2/F2_REPORT.md")
    assert old_ok is isinstance(path, PurePosixPath)


def test_f2_files_unchanged_except_declared():
    man = {p: h for h, p in (l.split("  ", 1) for l in (ROOT / "reports/f2/MANIFEST_F2.sha256").read_text().strip().splitlines())}
    changed = [rel for rel, h in man.items()
               if not (ROOT / rel).exists()
               or (sha(rel) != h and rel not in F3_DECLARED_MODIFIED and rel not in GH_DECLARED_MODIFIED)
               or (rel in GH_PINNED and sha(rel) != GH_PINNED[rel][1])]
    assert not changed, changed
    for rel in F3_DECLARED_MODIFIED:
        assert rel in man, rel


def test_f2_run_refuses_on_this_tree():
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "f2_run.py")], cwd=ROOT, capture_output=True, text=True)
    assert p.returncode != 0 and "reports/f2/ is frozen" in (p.stdout + p.stderr)
    test_reports_f2_frozen()
