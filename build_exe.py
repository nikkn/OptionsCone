"""Build the OptionsCone executable.

    python build_exe.py            one-file executable in dist/
    python build_exe.py --onedir   a folder instead: larger, starts faster

Build on the target platform: Windows produces OptionsCone.exe, macOS
OptionsCone.app. PyInstaller cannot cross-compile.

It first writes THIRD_PARTY_LICENSES.txt with the license text of every bundled
library, as their licenses require.
"""
from __future__ import annotations

import os
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Libraries the app imports directly; their dependencies are found by walking
# the requirements.
TOP = ["numpy", "pandas", "scipy", "yfinance", "pyarrow", "pywebview",
       "platformdirs", "curl_cffi", "requests", "lxml", "pyinstaller"]

# Pulled in by optional imports but never used; excluding them keeps the
# executable small.
EXCLUDE = ["tkinter", "matplotlib", "IPython", "notebook", "jupyter",
           "PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy", "gi", "pytest"]


def _deps(names):
    """Every installed distribution reachable from `names`."""
    try:
        from packaging.requirements import Requirement
    except ImportError:
        Requirement = None
    seen, todo = {}, list(names)
    while todo:
        n = todo.pop()
        key = n.lower().replace("_", "-")
        if key in seen:
            continue
        try:
            d = metadata.distribution(n)
        except metadata.PackageNotFoundError:
            continue
        seen[key] = d
        for r in d.requires or []:
            if Requirement is None:
                todo.append(r.split(";")[0].split("[")[0].split("<")[0]
                            .split(">")[0].split("=")[0].split("!")[0].strip())
                continue
            req = Requirement(r)
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            todo.append(req.name)
    return seen


def write_third_party():
    out = ["OptionsCone bundles the following third-party software.",
           "Each is distributed under its own license, reproduced below.", ""]
    py_lic = Path(sys.base_prefix) / "LICENSE.txt"
    if py_lic.exists():
        out += ["=" * 78, f"Python {sys.version.split()[0]}", "=" * 78,
                py_lic.read_text(encoding="utf-8", errors="replace"), ""]
    for key, d in sorted(_deps(TOP).items()):
        name, ver = d.metadata["Name"], d.version
        lic = (d.metadata.get("License-Expression") or d.metadata.get("License")
               or "").strip()
        out += ["=" * 78, f"{name} {ver}" + (f"  --  {lic.splitlines()[0][:70]}"
                                               if lic else ""), "=" * 78]
        texts = []
        for f in d.files or []:
            base = Path(str(f)).name.upper()
            if any(t in base for t in ("LICENSE", "LICENCE", "COPYING", "NOTICE")):
                try:
                    texts.append(Path(d.locate_file(f)).read_text(
                        encoding="utf-8", errors="replace"))
                except OSError:
                    pass
        out += texts or [lic or "(no license text shipped with the package; "
                                 "see the project's homepage)"]
        out.append("")
    p = ROOT / "THIRD_PARTY_LICENSES.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"third-party notices for {len(_deps(TOP))} packages -> {p.name}")


def build(onedir=False):
    import PyInstaller.__main__

    sep = os.pathsep
    data = [f"{ROOT / 'charts' / 'export_data.py'}{sep}charts",
            f"{ROOT / 'charts' / 'build_chart.py'}{sep}charts",
            f"{ROOT / 'LICENSE'}{sep}.",
            f"{ROOT / 'THIRD_PARTY_LICENSES.txt'}{sep}."]
    data += [f"{p}{sep}src" for p in sorted((ROOT / "src").glob("*.py"))]

    args = [str(ROOT / "app.py"), "--name", "OptionsCone", "--noconfirm", "--clean",
            "--windowed", "--onedir" if onedir else "--onefile",
            "--distpath", str(ROOT / "dist"),
            "--workpath", str(ROOT / "build"),
            "--specpath", str(ROOT / "build"),
            "--paths", str(ROOT / "src")]
    for d in data:
        args += ["--add-data", d]
    for pkg in ("yfinance", "curl_cffi", "webview", "pythonnet", "clr_loader", "lxml"):
        args += ["--collect-all", pkg]
    args += ["--hidden-import", "clr"]
    for m in EXCLUDE:
        args += ["--exclude-module", m]
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    write_third_party()
    build(onedir="--onedir" in sys.argv)
