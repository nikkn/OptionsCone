"""One data file per ticker, so a download only rewrites that ticker.

Two forms of each file:

    data/tickers/SYM.json      the export, merged into data/surface_data.json
                               for the all-in-one page
    charts/tickers/SYM.js      the same data wrapped as a script, loaded by
                               the page with a <script> tag (works in the app
                               and when the page is opened from disk)

plus charts/tickers/index.js, the list of tickers with their export time. The
export time doubles as a version, so the page never uses a stale cached file.
"""
from __future__ import annotations

import json
from datetime import datetime

from paths import sub


# Bumped when the export format changes; older files are re-exported from the
# archive on the next start, without a new download.
FORMAT = 7


def _json_dir():
    return sub("data") / "tickers"


def _js_dir():
    return sub("charts") / "tickers"


def write_ticker(sym, obj):
    """Store one ticker's export in both forms and refresh the index."""
    sym = sym.upper()
    for d in (_json_dir(), _js_dir()):
        d.mkdir(parents=True, exist_ok=True)
    obj = dict(obj)
    obj["_exported"] = datetime.now().strftime("%Y%m%dT%H%M%S")
    obj["_fmt"] = FORMAT
    txt = json.dumps(obj)
    (_json_dir() / f"{sym}.json").write_text(txt, encoding="utf-8")
    (_js_dir() / f"{sym}.js").write_text(
        f"OC_LOADED({json.dumps(sym)},{txt});\n", encoding="utf-8")


def held():
    """{symbol: export version} for every ticker with a data file."""
    d = _json_dir()
    if not d.exists():
        return {}
    out = {}
    for p in sorted(d.glob("*.json")):
        try:
            v = json.loads(p.read_text(encoding="utf-8")).get("_exported", "")
        except (OSError, ValueError):
            continue
        out[p.stem.upper()] = v
    return out


def stale():
    """Tickers whose data file predates the current export format."""
    d = _json_dir()
    out = []
    for p in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            fmt = json.loads(p.read_text(encoding="utf-8")).get("_fmt", 1)
        except (OSError, ValueError):
            continue
        if fmt < FORMAT:
            out.append(p.stem.upper())
    return out


def write_index():
    """The page's list of tickers, with a version for each."""
    _js_dir().mkdir(parents=True, exist_ok=True)
    idx = held()
    (_js_dir() / "index.js").write_text(
        f"OC_INDEX({json.dumps(idx)});\n", encoding="utf-8")
    return idx


def write_combined():
    """All tickers in one file, for the static snapshot page."""
    out = {}
    for p in sorted(_json_dir().glob("*.json")) if _json_dir().exists() else []:
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        obj.pop("_exported", None)
        out[p.stem.upper()] = obj
    (sub("data") / "surface_data.json").write_text(json.dumps(out))
    return out


def migrate_from_combined():
    """Split an older all-in-one export into per-ticker files, once."""
    if held():
        return 0
    f = sub("data") / "surface_data.json"
    if not f.exists():
        return 0
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    for sym, obj in data.items():
        if isinstance(obj, dict) and "expiries" in obj:
            write_ticker(sym, obj)
    write_index()
    return len(data)
