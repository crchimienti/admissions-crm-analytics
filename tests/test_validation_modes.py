"""Verification levels (v1.4.3-gh): analytical (portable) and graphical (strict), kept apart.

Niveles de verificación: analítica (portable) y gráfica (estricta), por separado.

* A difference only in PNG image bytes does not invalidate the portable analytical verification, and is reported.
* A numeric, textual, code or metadata difference invalidates both modes.
* Strict mode still detects different PNG images.
* The chart structure (data, titles, labels) is checked exactly, independent of pixel rendering.
* The versioned files are restored after a failure.
"""
from __future__ import annotations

import base64
import copy
import json
import subprocess
import sys

import pytest

from kpi_helpers import ROOT

sys.path.insert(0, str(ROOT / "scripts"))
import chart_signature as cs  # noqa: E402
import release_checks as rc  # noqa: E402
import release_run  # noqa: E402

NB = ROOT / "notebooks" / "admissions_analysis.ipynb"


@pytest.fixture(scope="module")
def reference():
    data = NB.read_bytes()
    return data, json.loads(data.decode("utf-8"))


def dump(nb: dict) -> bytes:
    return (json.dumps(nb, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def outputs(nb):
    for ci, c in enumerate(nb["cells"]):
        for oi, o in enumerate(c.get("outputs", [])):
            yield ci, oi, o


def with_png_changed(nb: dict, how_many: int = 1) -> dict:
    m = copy.deepcopy(nb)
    done = 0
    for _ci, _oi, o in outputs(m):
        if done < how_many and "image/png" in o.get("data", {}):
            raw = bytearray(base64.b64decode("".join(o["data"]["image/png"])))
            raw[-20] ^= 0x01                                       # one byte of the compressed image data
            o["data"]["image/png"] = base64.b64encode(bytes(raw)).decode()
            done += 1
    assert done == how_many
    return m


def test_identical_notebook_passes_both_modes(reference):
    data, _ = reference
    for mode in ("strict", "portable"):
        out = rc.notebook_outcome(mode, data, data)
        assert out == {"ok": True, "identical": True, "png": [], "other": []}


@pytest.mark.parametrize("n", [1, 5])
def test_png_only_difference_passes_portable_and_is_reported(reference, n):
    data, nb = reference
    out = rc.notebook_outcome("portable", dump(with_png_changed(nb, n)), data)
    assert out["ok"] and not out["identical"] and out["other"] == []
    assert len(out["png"]) == n and all(d["reference_size"] and d["rebuilt_size"] for d in out["png"])


def test_strict_mode_still_detects_different_png(reference):
    data, nb = reference
    out = rc.notebook_outcome("strict", dump(with_png_changed(nb)), data)
    assert not out["ok"] and not out["identical"] and len(out["png"]) == 1


def _first_text_output(nb):
    return next((ci, oi, o) for ci, oi, o in outputs(nb) if o.get("output_type") == "stream" and any(ch.isdigit() for ch in "".join(o["text"])))


@pytest.mark.parametrize("change", ["number_in_text", "table_html", "code", "execution_count", "metadata", "extra_output"])
def test_any_non_graphical_difference_fails_both_modes(reference, change):
    data, nb = reference
    m = with_png_changed(nb)                                  # even together with a PNG difference
    if change == "number_in_text":
        ci, oi, o = _first_text_output(m)
        text = "".join(o["text"])
        i = next(k for k, ch in enumerate(text) if ch.isdigit())
        o["text"] = text[:i] + str((int(text[i]) + 1) % 10) + text[i + 1:]
    elif change == "table_html":
        ci, oi, o = next(x for x in outputs(m) if "text/html" in x[2].get("data", {}))
        html = "".join(o["data"]["text/html"])
        i = next(k for k, ch in enumerate(html) if ch.isdigit())
        o["data"]["text/html"] = html[:i] + str((int(html[i]) + 1) % 10) + html[i + 1:]
    elif change == "code":
        cell = next(c for c in m["cells"] if c["cell_type"] == "code")
        src = "".join(cell["source"])
        cell["source"] = src.replace("import", "import  ", 1)
    elif change == "execution_count":
        cell = next(c for c in m["cells"] if c["cell_type"] == "code")
        cell["execution_count"] = (cell["execution_count"] or 0) + 100
    elif change == "metadata":
        m["metadata"]["language_info"]["name"] = "python3"
    elif change == "extra_output":
        cell = next(c for c in m["cells"] if c["cell_type"] == "code")
        cell["outputs"].append({"output_type": "stream", "name": "stdout", "text": "extra\n"})
    for mode in ("portable", "strict"):
        out = rc.notebook_outcome(mode, dump(m), data)
        assert not out["ok"] and out["other"], (mode, change)


def test_no_volatile_field_is_exempted():
    assert rc.ALLOWED_VOLATILE == frozenset()


def test_unreadable_rebuilt_notebook_fails(reference):
    data, _ = reference
    out = rc.notebook_outcome("portable", b"not a notebook", data)
    assert not out["ok"] and out["other"]


# ----- chart structure ------------------------------------------------------- #
@pytest.fixture(scope="module")
def chart_reference():
    return json.loads((ROOT / "tests" / "chart_signature_reference.json").read_text(encoding="utf-8"))


def test_chart_structure_matches_the_reference():
    p = subprocess.run([sys.executable, str(ROOT / "scripts" / "chart_signature.py"), "--check"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "5 charts — identical to the reference" in p.stdout


def test_chart_reference_describes_the_five_charts(chart_reference):
    titles = [f["axes"][0]["title"][1] for f in chart_reference]
    assert len(chart_reference) == 5 and all("(synthetic)" in t or "synthetic" in t for t in titles)
    assert any(f["axes"][0]["lines"] for f in chart_reference) and any(f["axes"][0]["rectangles"] for f in chart_reference)


@pytest.mark.parametrize("change", ["title", "label", "legend", "line_data", "bar_height", "annotation", "chart_missing"])
def test_chart_structure_detects_changes(chart_reference, change):
    cur = copy.deepcopy(chart_reference)
    by = {"title": lambda: cur[0]["axes"][0]["title"].__setitem__(1, "Other title"),
          "label": lambda: cur[0]["axes"][0].__setitem__("ylabel", "other"),
          "legend": lambda: next(f for f in cur if f["axes"][0]["legend"])["axes"][0]["legend"].reverse(),
          "line_data": lambda: next(f for f in cur if f["axes"][0]["lines"])["axes"][0]["lines"][0]["y"].__setitem__(0, 0.123),
          "bar_height": lambda: next(f for f in cur if f["axes"][0]["rectangles"])["axes"][0]["rectangles"][0].__setitem__("h", 1.0),
          "annotation": lambda: next(f for f in cur if f["axes"][0]["texts"])["axes"][0]["texts"][0].__setitem__("text", "x"),
          "chart_missing": lambda: cur.pop()}
    by[change]()
    assert cs.diff(cur, chart_reference), change
    assert cs.diff(chart_reference, chart_reference) == []


# ----- restoration after a failure ------------------------------------------- #
def test_restore_puts_back_modified_and_deleted_files(tmp_path):
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "docs" / "img").mkdir(parents=True)
    saved = {"notebooks/admissions_analysis.ipynb": b"reference notebook", "docs/img/a.png": b"\x89PNG reference"}
    (tmp_path / "notebooks" / "admissions_analysis.ipynb").write_bytes(b"windows rendering")   # overwritten by a run
    back = release_run.restore(saved, tmp_path)                                              # docs/img/a.png deleted
    assert sorted(back) == sorted(saved)
    for rel, data in saved.items():
        assert (tmp_path / rel).read_bytes() == data
    assert release_run.restore(saved, tmp_path) == []                                        # nothing left to restore


def test_restorable_files_cover_the_versioned_generated_files():
    assert set(release_run.RESTORABLE) == {"data/leads.csv", "data/activities.csv", "data/dq_ground_truth.csv",
                                           "notebooks/admissions_analysis.ipynb", "docs/img/funnel_mature_cohorts.png",
                                           "docs/img/main_kpi_by_cohort.png", "docs/img/show_rate_by_month.png"}


def test_portable_reports_stay_outside_the_reference_manifests():
    assert release_run.PORTABLE_OUT == ROOT / "build" / "portable"
    assert rc.is_ignored("build/portable/PORTABLE_REPORT.md")
    text, _tree_id = release_run.release_manifest()            # what the release manifest would list right now
    assert not any(line.split("  ", 1)[1].startswith("build/") for line in text.splitlines())
    for manifest in ("reports/release/MANIFEST_RELEASE_v1.4.2.sha256", "reports/f3/MANIFEST_F3.sha256"):
        assert "build/" not in (ROOT / manifest).read_text(encoding="utf-8")
