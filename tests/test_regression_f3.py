"""F3 is frozen since v1.4.0-gh (v1.3.1-f3, approved on 2026-10-14).

F3 queda congelada desde v1.4.0-gh.

* reports/f3/ is byte-identical to the v1.3.1-f3 delivery (pinned hashes, exact file list).
* Every file of the F3 manifest is unchanged, except the declared v1.4.0-gh changes (code files pinned).
* scripts/f3_run.py refuses to run on this tree before touching any file.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys

from kpi_helpers import ROOT
from release_declared import GH_DECLARED_MODIFIED, GH_PINNED

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


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def test_reports_f3_frozen():
    for rel, h in F3_REPORTS.items():
        assert sha(rel) == h, rel
    present = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "reports" / "f3").iterdir())
    assert present == sorted(F3_REPORTS)


def test_f3_files_unchanged_except_declared():
    man = {p: h for h, p in (l.split("  ", 1) for l in
                             (ROOT / "reports/f3/MANIFEST_F3.sha256").read_text(encoding="utf-8").strip().splitlines())}
    changed = [rel for rel, h in man.items()
               if not (ROOT / rel).exists()
               or (sha(rel) != h and rel not in GH_DECLARED_MODIFIED)
               or (rel in GH_PINNED and sha(rel) != GH_PINNED[rel][1])]
    assert not changed, changed
    for rel, (old, _new, _why) in GH_PINNED.items():
        assert man[rel] == old, rel                    # the recorded F3 hash is the one the change started from


def test_f3_run_refuses_on_this_tree():
    p = subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "f3_run.py")], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8")
    assert p.returncode != 0 and "reports/f3/ is frozen" in (p.stdout + p.stderr)
    test_reports_f3_frozen()
