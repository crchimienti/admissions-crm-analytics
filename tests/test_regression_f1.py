"""F2 regression against the frozen F0 (v1.0.0-f0) and F1 (v1.1.0-f1) references.

Regresión de F2 contra las referencias congeladas de F0 y F1.

* baseline/ (F0) and reports/f1/ (F1) are byte-identical to their frozen versions.
* Every file of the F1 manifest is unchanged, except the files F2 declares as modified. src/metrics.py is the only
  modified source module: it must be exactly the authorised v1.2.1-f2 revision (pinned hash), nothing else.
* The 47 metrics computed through CSV -> canonical -> admissions adapter -> src/metrics.py equal
  baseline/metrics_v1.json and reports/f1/metrics_f1.json: ids, order, descriptive fields, numerators,
  denominators and values (6 decimals, no extra tolerance).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402
from release_declared import GH_DECLARED_MODIFIED, GH_PINNED  # noqa: E402
from canonical import mapping  # noqa: E402
from canonical.adapters import admissions as ad  # noqa: E402
from canonical.validate import validate  # noqa: E402

F0_TREE_ID = "eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df"
F1_TREE_ID = "9206c83e2b6fea8042f748621542179b4fbb885ca785dff93f7d711053aa9651"
F0_OUTSIDE_MANIFEST = {
    "baseline/F0_REPORT.md": "573dc315e20b5cbbc1268952209b06eb1ef549fcf200f95ac38920ba4156c84f",
    "baseline/F0_REPORT.es.md": "418a2a5a2cd59e031493ae64f31a5da40193af18c35f9e44e9daf10a8939daec",
}
# reports/f1/ as delivered in admissions-crm-analytics-v1.1.0-f1.zip (frozen since F2)
F1_REPORTS = {
    "reports/f1/MANIFEST_F1.sha256": F1_TREE_ID,
    "reports/f1/metrics_f1.json": "4538857acc710a84880e2cfdd72bbe43bfbe1d1cfda27130c73253ca83210959",
    "reports/f1/F1_REPORT.md": "a10de2fd7d97880a5a93def4a17c437d749579a85c75abbfae12041ea878f969",
    "reports/f1/F1_REPORT.es.md": "205afee143064287641b0d12b548d0fc179caae2f5028103bffac60f4dff8fe3",
    "reports/f1/F0_COMPARISON.md": "5ed91a354b773248af040e6214179733207a15f0d36950397946c7f1d6f5251c",
    "reports/f1/F0_COMPARISON.es.md": "18657f11ef901ef05b77452e5c0a8b13883d1664b8758eca8657ad6f047fd79d",
}
# F1 files that F2 changes on purpose (anything else in the F1 manifest must be byte-identical)
F2_DECLARED_MODIFIED = {
    "README.md": "F2 section, repository structure and how to run (no figure changed)",
    "README.es.md": "sección F2, estructura y cómo ejecutar (ninguna cifra cambia)",
    "scripts/f1_run.py": "guard only: refuses to run on the F2 tree (reports/f1/ is frozen)",
    "scripts/export_metrics.py": "guard only: refuses to write reports/f1/ on the F2 tree",
    "src/metrics.py": "v1.2.1-f2 authorised robustness fix (zero denominators, empty appointment structures); same 47 values",
}
F1_METRICS_SHA = "6b7f1defa8995c71684298f5df36d7bc4dd5039b5283a95b459b144469574c3b"   # src/metrics.py in v1.1.0-f1
AUTHORISED_METRICS_SHA = "c5503ccd4ac5d96555d0d05db3553701b261246d469c4281f4fd545ad757628a"   # src/metrics.py in v1.2.1-f2


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def manifest(rel):
    return {p: h for h, p in (r.split("  ", 1) for r in (ROOT / rel).read_text().strip().splitlines())}


def test_f0_frozen():
    assert sha("baseline/MANIFEST.sha256") == F0_TREE_ID
    for rel, h in manifest("baseline/MANIFEST.sha256").items():
        if rel.startswith("baseline/"):
            assert sha(rel) == h, rel
    for rel, h in F0_OUTSIDE_MANIFEST.items():
        assert sha(rel) == h, rel
    assert sorted(p.name for p in (ROOT / "baseline").iterdir()) == sorted(
        ["BASELINE.md", "BASELINE.es.md", "F0_REPORT.md", "F0_REPORT.es.md", "MANIFEST.sha256", "environment.txt", "metrics_v1.json"])


def test_f1_reports_frozen():
    for rel, h in F1_REPORTS.items():
        assert sha(rel) == h, rel
    assert sorted(p.name for p in (ROOT / "reports" / "f1").iterdir()) == sorted(Path(r).name for r in F1_REPORTS)


def test_f1_files_unchanged_except_declared():
    changed = []
    for rel, h in manifest("reports/f1/MANIFEST_F1.sha256").items():
        p = ROOT / rel
        if not p.exists():
            changed.append(("REMOVED", rel))
        elif sha(rel) != h and rel not in F2_DECLARED_MODIFIED and rel not in GH_DECLARED_MODIFIED:
            changed.append(("MODIFIED", rel))
        elif rel in GH_PINNED and sha(rel) != GH_PINNED[rel][1]:
            changed.append(("NOT THE AUTHORISED v1.4.0-gh REVISION", rel))
    assert not changed, changed


def test_metrics_module_generator_and_data_untouched():
    f1 = manifest("reports/f1/MANIFEST_F1.sha256")
    for rel in ("src/checks.py", "src/generate_data.py", "src/calendar_utils.py",
                "config/simulation_params.yaml", "data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv"):
        if rel in GH_PINNED:   # declared v1.4.0-gh line-ending fix: F1 hash recorded, new revision pinned
            assert f1[rel] == GH_PINNED[rel][0] and sha(rel) == GH_PINNED[rel][1], rel
            continue
        assert sha(rel) == f1[rel], rel


def test_metrics_py_is_exactly_the_authorised_revision():
    f1 = manifest("reports/f1/MANIFEST_F1.sha256")
    assert f1["src/metrics.py"] == F1_METRICS_SHA
    assert sha("src/metrics.py") == AUTHORISED_METRICS_SHA != F1_METRICS_SHA


def test_direct_route_reproduces_the_f1_document_byte_for_byte():
    """metrics.py (v1.2.1-f2) on the generated data writes exactly reports/f1/metrics_f1.json (all sections)."""
    ctx = metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")
    doc = metrics.baseline_document(ctx, "v1.1.0-f1", ROOT)
    assert json.dumps(doc, indent=2, ensure_ascii=False) + "\n" == (ROOT / "reports" / "f1" / "metrics_f1.json").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def canonical_metrics():
    can = validate(mapping.map_directory(ROOT / "data"))
    ad.check_profile(can)
    return ad.evaluate(can)


def _strip(entry):
    return {k: v for k, v in entry.items() if k != "status"}


@pytest.mark.parametrize("ref", ["baseline/metrics_v1.json", "reports/f1/metrics_f1.json"])
def test_47_metrics_through_canonical_route(canonical_metrics, ref):
    reference = json.loads((ROOT / ref).read_text(encoding="utf-8"))["metrics"]
    got = canonical_metrics["baseline_metrics"]
    assert all(e["status"] == "available" for e in got)
    assert [_strip(e) for e in got] == reference
    rec = metrics.reconcile({"metrics": [_strip(e) for e in got]}, {"metrics": reference})
    assert int(rec.match.astype(bool).sum()) == 47 and rec.attrs["missing_from_document"] == []


def test_admissions_catalogue_on_generated_data(canonical_metrics):
    """The generated CSV is a milestone dataset: 24 metrics + first_entry available, the 6 HF indicators not."""
    cat = canonical_metrics["catalogue"]
    na = [(e["id"], e["reason"]) for e in cat if e["status"] == "not_available"]
    assert na == [(i, "HF") for i in ("entry_count", "regression_events", "regression_rate", "reopen_events",
                                      "reopen_rate", "time_in_stage")]
    assert sum(e["status"] == "available" for e in cat) == 25
