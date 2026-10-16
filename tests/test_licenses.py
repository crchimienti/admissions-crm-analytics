"""Licences (v1.4.4-gh): MIT for code, CC BY 4.0 for content, third-party notices kept.

Licencias: MIT para el código, CC BY 4.0 para el contenido, avisos de terceros conservados.
"""
from __future__ import annotations

import hashlib
import re

import pytest

from kpi_helpers import ROOT

HOLDER = "Carlos Eduardo Rodriguez Chimienti"
REPO_URL = "https://github.com/crchimienti/admissions-crm-analytics/"
# Official MIT text (SPDX license list, text/MIT.txt) with the holder and year filled in; compared word for word.
MIT_OFFICIAL = f"""MIT License

Copyright (c) 2026 {HOLDER}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""
OFL_SHA256 = "262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a"
ATTRIBUTION = f"{HOLDER} — Admissions CRM Analytics"


def words(text):
    return re.sub(r"\s+", " ", text).strip()


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_license_is_the_official_mit_text_with_holder_and_year():
    assert words(read("LICENSE")) == words(MIT_OFFICIAL)
    assert read("LICENSE").splitlines()[2] == f"Copyright (c) 2026 {HOLDER}"


def test_license_content_identifies_cc_by_4_0_and_its_scope():
    text = read("LICENSE-CONTENT")
    for must in (f"Copyright (c) 2026 {HOLDER}", "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                 "SPDX identifier: CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/legalcode",
                 "to the extent that copyright or similar", "narrative (Markdown) cells", "code cells of the notebook",
                 "MIT License", "SIL Open Font License, Version 1.1", "The Inter Project Authors", ATTRIBUTION,
                 "indicate whether changes were made", f"Repository: {REPO_URL}",
                 "100 % synthetic", "AI assistance"):
        assert must in text, must
    # Spanish summary with the same scope
    for must in ("CC BY 4.0", "celdas de código del notebook", "celdas narrativas", "SIL Open Font License 1.1",
                 f"«{ATTRIBUTION}»", f"Repositorio:\n  {REPO_URL}", "demo local de app/"):
        assert must in text, must


def test_paths_named_in_the_licence_scope_exist():
    text = read("LICENSE-CONTENT")
    for path in ("README.md", "README.es.md", "CHANGELOG.md", "docs/img/", "assets/fonts/inter/FONTS.md", "baseline/",
                 "reports/", "scripts/notebook_conclusions.md", "data/", "tests/fixtures/", "notebooks/admissions_analysis.ipynb",
                 "src/", "scripts/", "tests/", "app/", ".streamlit/", "schema/", "profiles/", "config/", ".github/", ".gitignore", ".gitattributes",
                 "assets/fonts/inter/OFL.txt", "LICENSE"):
        assert path in text, path
        assert (ROOT / path.rstrip("/")).exists(), path


def test_no_repository_url_is_invented():
    """Only the published repository (v1.5.0-app) and the upstream Inter project are named on GitHub."""
    allowed = (REPO_URL, REPO_URL.rstrip("/") + ".git", "https://github.com/rsms/inter")
    for rel in ("LICENSE", "LICENSE-CONTENT", "README.md", "README.es.md", "app/app_data.py"):
        urls = re.findall(r"https?://[^\s)>\]`\"]+", read(rel))
        assert all(not u.startswith("https://github.com/") or u.startswith(allowed) for u in urls), (rel, urls)
    for rel in ("LICENSE-CONTENT", "README.md", "README.es.md"):
        assert REPO_URL in read(rel), rel
    assert "once the repository is published" not in read("LICENSE-CONTENT")
    assert "se añadirá" not in read("LICENSE-CONTENT")


def test_third_party_font_licence_and_notices_are_unchanged():
    ofl = ROOT / "assets" / "fonts" / "inter" / "OFL.txt"
    assert hashlib.sha256(ofl.read_bytes()).hexdigest() == OFL_SHA256
    fonts_md = read("assets/fonts/inter/FONTS.md")
    assert "SIL Open Font License" in fonts_md and "The Inter Project Authors" in fonts_md
    assert "Inter UI and Inter is a trademark of rsms" in fonts_md
    assert HOLDER not in fonts_md and HOLDER not in ofl.read_text(encoding="utf-8")      # not attributed to the project


@pytest.mark.parametrize("name,phrases", [
    ("README.md", ["[`LICENSE`](LICENSE)", "[`LICENSE-CONTENT`](LICENSE-CONTENT)", "[`OFL.txt`](assets/fonts/inter/OFL.txt)",
                   f"Copyright (c) 2026 {HOLDER}", "**code cells**", "**narrative cells, charts and outputs**",
                   "to the extent rights exist", "Third-party material keeps its own licences", ATTRIBUTION]),
    ("README.es.md", ["[`LICENSE`](LICENSE)", "[`LICENSE-CONTENT`](LICENSE-CONTENT)", "[`OFL.txt`](assets/fonts/inter/OFL.txt)",
                      f"Copyright (c) 2026 {HOLDER}", "**celdas de código**", "**celdas narrativas, gráficos y salidas**",
                      "en la medida en que existan derechos", "Los materiales de terceros conservan", ATTRIBUTION]),
])
def test_readme_licence_section(name, phrases):
    text = read(name)
    for ph in phrases:
        assert ph in text, (name, ph)
    assert "not chosen yet" not in text and "todavía no elegida" not in text


def test_windows_result_is_recorded_as_reported_and_scoped():
    en, es = read("README.md"), read("README.es.md")
    assert "**portable analytical level verified by the project owner** with v1.4.3-gh" in en
    assert "**Strict graphical level not passed**" in en and "Not run by the maintainer of this delivery on Windows" in en
    assert "**nivel analítico portable verificado por la responsable del proyecto** con v1.4.3-gh" in es
    assert "**Nivel gráfico estricto no aprobado**" in es
    for text in (en, es):
        assert "FreeType" not in text.split("## Repository map")[0].split("## Mapa del repositorio")[0]   # no cause asserted
    assert "| macOS (Apple Silicon, Intel ≥ 10.15) | **prepared, not yet verified**" in en
