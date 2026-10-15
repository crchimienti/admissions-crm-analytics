"""Reference chart rendering for the notebook (v1.4.1-gh): fonts and matplotlib settings fixed by the project.

Renderizado de referencia de los gráficos del notebook: fuentes y ajustes de matplotlib fijados por el proyecto.

The F1 notebook images were drawn with Inter 4.000 (Regular and Bold) and text hinting disabled. This module makes that
rendering independent of the machine:
  * it registers the two Inter files shipped in assets/fonts/inter/ (hashes pinned below) — no system installation;
  * it resets matplotlib to its built-in defaults, so no user or site matplotlibrc changes the charts;
  * it removes any other font named "Inter" from matplotlib's list, so a different system copy is never picked;
  * it sets font.family = Inter, sans-serif, DejaVu Sans and text.hinting = no_hinting explicitly;
  * it checks that Inter Regular and Bold resolve to the project files. If a file is missing, its hash differs or the
    resolution fails, it raises RenderingError: there is no silent fallback to another font.

scripts/build_notebook.py runs `configure()` inside the notebook kernel before the first cell (IPython exec_lines,
which neither prints into the notebook nor changes execution counts), so the notebook cells and their bytes stay
exactly those of F1. Nothing is downloaded and no external MATPLOTLIBRC is read.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts" / "inter"
FONTS = {   # file -> SHA-256 (Inter 4.000, git-a52131595; provenance in assets/fonts/inter/FONTS.md)
    "Inter-Regular.otf": "be6d709dcb730ddaf050cbdae6fe89bd56d5d14dc66885639bbf6f06bd03521b",
    "Inter-Bold.otf": "00fd6f4691ee8884a33b46bf45851b341927c37c30064f558e1befb242971c49",
}
RC = {"font.family": ["Inter", "sans-serif", "DejaVu Sans"], "text.hinting": "no_hinting"}


class RenderingError(RuntimeError):
    pass


def check_files() -> list[Path]:
    """The two font files exist and have the pinned hashes."""
    paths = []
    for name, digest in FONTS.items():
        p = FONT_DIR / name
        if not p.is_file():
            raise RenderingError(f"reference font missing: {p.relative_to(ROOT).as_posix()} (see assets/fonts/inter/FONTS.md)")
        if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise RenderingError(f"reference font changed: {p.relative_to(ROOT).as_posix()} does not have the pinned SHA-256")
        paths.append(p)
    return paths


def configure() -> dict:
    """Register the project fonts, apply the reference settings and verify the resolution. Returns what was used."""
    import matplotlib as mpl
    from matplotlib import font_manager as fm

    paths = check_files()
    mpl.rcdefaults()                                    # built-in defaults: ignore any user or site matplotlibrc
    project = {str(p.resolve()) for p in paths}
    fm.fontManager.ttflist = [f for f in fm.fontManager.ttflist
                              if f.name != "Inter" or str(Path(f.fname).resolve()) in project]
    for p in paths:
        if str(p.resolve()) not in {str(Path(f.fname).resolve()) for f in fm.fontManager.ttflist}:
            fm.fontManager.addfont(str(p))
    if hasattr(fm.fontManager, "_findfont_cached"):     # forget any lookup made before the registration
        fm.fontManager._findfont_cached.cache_clear()
    mpl.rcParams.update(RC)
    used = {}
    for weight, name in (("normal", "Inter-Regular.otf"), ("bold", "Inter-Bold.otf")):
        found = fm.findfont(fm.FontProperties(family=RC["font.family"], weight=weight), fallback_to_default=False)
        if Path(found).resolve() != (FONT_DIR / name).resolve():
            raise RenderingError(f"Inter {weight} resolves to {found}, not to the project file {name}")
        used[weight] = Path(found).name
    return {"fonts": used, **{k: mpl.rcParams[k] for k in RC}}


def kernel_setup() -> None:
    """Called in the notebook kernel: configure, or stop the kernel (exit code 3) so the build fails loudly."""
    import os
    import sys
    try:
        configure()
    except Exception as e:  # noqa: BLE001 — any failure must stop the build, never fall back to another font
        sys.stderr.write(f"reference rendering failed: {e}\n")
        sys.stderr.flush()
        os._exit(3)


def kernel_exec_line() -> str:
    """A single line for IPython exec_lines; it binds no name in the notebook namespace."""
    scripts = repr(str(ROOT / "scripts"))
    return (f"__import__('sys').path.insert(0, {scripts}); __import__('notebook_rendering').kernel_setup(); "
            f"__import__('sys').path.remove({scripts})")
