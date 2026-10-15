"""F1 regression against the frozen F0 reference (v1.0.0-f0).

Regresión de F1 contra la referencia congelada de F0.

* baseline/ and the protected files are byte-identical to F0 (hashes from baseline/MANIFEST.sha256, whose own
  SHA-256 is the F0 tree id).
* The 47 metrics computed by src/metrics.py equal baseline/metrics_v1.json: ids and order, descriptive fields,
  numerators, denominators, and values at the reference rounding (6 decimals) with no extra tolerance.
* reports/f1/metrics_f1.json equals metrics_v1.json byte for byte except `baseline_id`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import metrics  # noqa: E402
from release_declared import GH_PINNED  # noqa: E402

F0_TREE_ID = "eb4f60681f71e88a8c581d4a68670c19d8be661e4ca86298cffc63dfb4d682df"
# F0 files deliberately outside the F0 manifest (they record run timings); hashes taken from the v1.0.0-f0 ZIP.
F0_FROZEN_OUTSIDE_MANIFEST = {
    "baseline/F0_REPORT.md": "573dc315e20b5cbbc1268952209b06eb1ef549fcf200f95ac38920ba4156c84f",
    "baseline/F0_REPORT.es.md": "418a2a5a2cd59e031493ae64f31a5da40193af18c35f9e44e9daf10a8939daec",
}
# Files F1 must not change (generator, configuration, data, checks, definitions, existing tests, conclusions).
PROTECTED = ["src/generate_data.py", "src/checks.py", "src/calendar_utils.py", "config/simulation_params.yaml",
             "data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv",
             "docs/assumptions.md", "docs/assumptions.es.md", "docs/data_dictionary.md", "docs/data_dictionary.es.md",
             "docs/kpi_definitions.md", "docs/kpi_definitions.es.md", "tests/test_integrity.py", "tests/test_baseline.py",
             "scripts/notebook_conclusions.md", "requirements.txt", ".gitignore"]
DESCRIPTIVE = ["id", "label_en", "label_es", "unit", "kind", "population", "numerator", "denominator",
               "time_basis", "definition_ref"]
ROUND_BOUND = 5e-7   # the only tolerance: what rounding to 6 decimals allows


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def f0_manifest():
    rows = (ROOT / "baseline" / "MANIFEST.sha256").read_text().strip().splitlines()
    return {p: h for h, p in (r.split("  ", 1) for r in rows)}


@pytest.fixture(scope="module")
def reference():
    return json.loads((ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ctx():
    return metrics.load_context(ROOT / "data", ROOT / "config" / "simulation_params.yaml")


@pytest.fixture(scope="module")
def document(ctx):
    return metrics.baseline_document(ctx, "v1.1.0-f1", ROOT)


# ----- F0 stays frozen ----------------------------------------------------- #
def test_f0_manifest_is_the_frozen_one():
    assert sha("baseline/MANIFEST.sha256") == F0_TREE_ID


def test_baseline_folder_is_byte_identical_to_f0():
    man = f0_manifest()
    in_manifest = {p for p in man if p.startswith("baseline/")}
    assert in_manifest == {"baseline/BASELINE.md", "baseline/BASELINE.es.md", "baseline/environment.txt",
                           "baseline/metrics_v1.json"}
    for p in in_manifest:
        assert sha(p) == man[p], f"{p} changed since F0"
    for p, h in F0_FROZEN_OUTSIDE_MANIFEST.items():
        assert sha(p) == h, f"{p} changed since F0"
    present = {f"baseline/{x.name}" for x in (ROOT / "baseline").iterdir()}
    assert present == in_manifest | set(F0_FROZEN_OUTSIDE_MANIFEST) | {"baseline/MANIFEST.sha256"}, "unexpected file in baseline/"


@pytest.mark.parametrize("path", PROTECTED)
def test_protected_file_unchanged_since_f0(path):
    if path in GH_PINNED:   # declared v1.4.0-gh change: the F0 hash is recorded and the new revision is pinned
        old, new, change = GH_PINNED[path]
        assert f0_manifest()[path] == old and sha(path) == new, f"{path} is not the authorised v1.4.0-gh revision ({change})"
        return
    assert sha(path) == f0_manifest()[path], f"{path} changed since F0"


# ----- 47 metrics ----------------------------------------------------------- #
def test_same_47_metric_ids_in_the_same_order(document, reference):
    assert [m["id"] for m in document["metrics"]] == [m["id"] for m in reference["metrics"]]
    assert len(document["metrics"]) == 47


def test_descriptive_fields_numerators_denominators_equal(document, reference):
    for new, ref in zip(document["metrics"], reference["metrics"]):
        for f in DESCRIPTIVE:
            assert new[f] == ref[f], (ref["id"], f)
        assert new["numerator_value"] == ref["numerator_value"], ref["id"]
        assert new["denominator_value"] == ref["denominator_value"], ref["id"]
        if ref["numerator_value"] is not None:
            assert isinstance(new["numerator_value"], int)
        if ref["denominator_value"] is not None:
            assert isinstance(new["denominator_value"], int)


def test_values_equal_at_reference_rounding(ctx, reference):
    raw = {m.id: m for m in metrics.baseline_metrics(ctx)}
    for ref in reference["metrics"]:
        m = raw[ref["id"]]
        if ref["kind"] == "count":
            assert int(m.value) == ref["value"] and isinstance(ref["value"], int), ref["id"]
            continue
        v = float(m.value)
        assert round(v, 6) == ref["value"], (ref["id"], v, ref["value"])          # exact at 6 decimals
        assert math.isclose(v, ref["value"], rel_tol=0, abs_tol=ROUND_BOUND), ref["id"]


def test_other_sections_identical(document, reference):
    for key in ("schema_version", "note", "seed", "snapshot_date", "maturity_days", "inputs_sha256",
                "cohort_maturity", "anomaly_reconciliation", "logic_checks"):
        assert document[key] == reference[key], key
    assert document["baseline_id"] == "v1.1.0-f1" and reference["baseline_id"] == "v1.0.0-f0"


def test_document_is_byte_identical_except_version_id(document, reference):
    f0_bytes = (ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8")
    renamed = dict(document, baseline_id="v1.0.0-f0")
    assert json.dumps(renamed, indent=2, ensure_ascii=False) + "\n" == f0_bytes


def test_exported_f1_file_matches_f0_except_version_id():
    out = ROOT / "reports" / "f1" / "metrics_f1.json"
    if not out.exists():
        pytest.fail("reports/f1/metrics_f1.json missing: run `python scripts/export_metrics.py` first")
    f1 = json.loads(out.read_text(encoding="utf-8"))
    assert f1["baseline_id"] == "v1.1.0-f1"
    f1["baseline_id"] = "v1.0.0-f0"
    assert json.dumps(f1, indent=2, ensure_ascii=False) + "\n" == (ROOT / "baseline" / "metrics_v1.json").read_text(encoding="utf-8")


def test_reconcile_reports_47_of_47(document, reference):
    rec = metrics.reconcile(document, reference)
    assert len(rec) == 47 and bool(rec.match.all()) and rec.attrs["missing_from_document"] == []


@pytest.mark.parametrize("field,change", [
    ("value", lambda v: v + 1e-6), ("numerator_value", lambda v: v + 1), ("denominator_value", lambda v: v - 1),
    ("population", lambda v: v + " (changed)"), ("time_basis", lambda v: "period"), ("unit", lambda v: "appointment")])
def test_any_altered_field_is_detected(document, reference, field, change):
    bad = copy.deepcopy(document)
    m = next(x for x in bad["metrics"] if x["id"] == "main_kpi_interviews_held_over_opportunities")
    m[field] = change(m[field])
    rec = metrics.reconcile(bad, reference)
    assert not bool(rec.loc["main_kpi_interviews_held_over_opportunities", "match"])
    with pytest.raises(AssertionError):
        test_descriptive_fields_numerators_denominators_equal(bad, reference)
        assert bad["metrics"][5]["value"] == reference["metrics"][5]["value"]
