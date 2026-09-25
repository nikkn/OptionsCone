"""OptionsCone desktop app.

    python app.py                  open the app
    python app.py --selftest AAPL  run the pipeline once, without a window

The chart is an HTML page shown in its own window. Its ticker box and buttons
call back into Python here: each requested chain is downloaded, archived and
exported to its own data file, in a background thread, with progress shown in
the page.

Packaged, the data lives in the user's application-data folder (see
src/paths.py); run from source, it stays in the project folder.

Copyright (C) 2026 Nikolai Alexander. Licensed under the GNU Affero General
Public License v3.0 or later; see LICENSE.
"""
from __future__ import annotations

import io
import json
import os
import runpy
import subprocess
import sys
import threading
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path

# Location of the bundled code: the unpack folder when frozen, the project
# folder from source.
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(BUNDLE / "src"))

from paths import home, sub  # noqa: E402

# Imported here so the packager bundles every dependency of the pipeline
# scripts, which run through runpy.
import numpy  # noqa: E402,F401
import pandas  # noqa: E402,F401
import scipy.optimize  # noqa: E402,F401
import scipy.stats  # noqa: E402,F401
import yfinance  # noqa: E402,F401
import pyarrow  # noqa: E402,F401
# yfinance loads lxml only on demand (earnings calendar), so it is imported
# explicitly for the packager.
import lxml.etree  # noqa: E402,F401
import lxml.html  # noqa: E402,F401
import american, archive, barrier, chain, dataquality, dividends  # noqa: E402,F401,E401
import earnings, expiries, montecarlo, optionev, quality, realized  # noqa: E402,F401,E401
import varswap  # noqa: E402,F401
import tickerfiles  # noqa: E402

APP_NAME = "OptionsCone"


def page_path() -> Path:
    # The app page: an empty shell that loads each ticker's data file on
    # demand. optionscone.html is the all-in-one version.
    return sub("charts") / "app.html"


def build_shell():
    """Rebuild the app page at every start, so it matches the running version.
    """
    tickerfiles.migrate_from_combined()
    tickerfiles.write_index()
    _run_script("charts/build_chart.py", ["--app"])


def log_path() -> Path:
    return sub("logs") / "optionscone.log"


class _Tee(io.TextIOBase):
    """Console output to the log file, and each finished line to a callback.

    A windowed executable has no console; the pipeline's printed lines become
    the progress text.
    """

    encoding = "utf-8"

    def __init__(self, logf, on_line=None):
        self._logf, self._on_line, self._buf = logf, on_line, ""

    def writable(self):
        return True

    def write(self, s):
        s = s if isinstance(s, str) else str(s)
        self._logf.write(s)
        self._logf.flush()
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            line = line.strip()
            if line and self._on_line:
                try:
                    self._on_line(line)
                except Exception:
                    pass
        return len(s)

    def flush(self):
        self._logf.flush()


def _run_script(rel, args):
    """Run one of the pipeline scripts as if from the command line."""
    path = BUNDLE / rel
    saved = sys.argv
    sys.argv = [str(path), *args]
    try:
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as e:
        if e.code not in (None, 0):
            raise RuntimeError(str(e.code)) from None
    finally:
        sys.argv = saved


_STEP = {"text": ""}

# Progress bar state. Each ticker counts equally; within a ticker the chain
# download fills up to 35%, the solves up to 60%, and the export the rest. The
# export-only update uses the whole range for the export. The fraction never
# moves backwards.
_PROG = {"i": 1, "n": 1, "sub": 0.0, "nexp": 0, "rows": 0, "export_only": False}


def _prog_start(n, export_only=False):
    _PROG.update(i=1, n=max(1, n), sub=0.0, nexp=0, rows=0,
                 export_only=export_only)


def _prog_ticker(i):
    _PROG.update(i=i, sub=0.0, nexp=0, rows=0)


def _prog_frac():
    return min(1.0, ((_PROG["i"] - 1) + _PROG["sub"]) / _PROG["n"])


def _prog_line(line):
    """Move the fraction on from one line of the pipeline's own output."""
    import re
    m = re.search(r": expiry (\d+)/(\d+)", line)
    if _PROG["export_only"]:
        if m:
            _PROG["sub"] = max(_PROG["sub"], int(m[1]) / max(1, int(m[2])))
        return _prog_frac()
    e = re.search(r"expiries=(\d+)", line)
    if e:
        _PROG["nexp"], _PROG["rows"] = int(e[1]), 0
    elif "raw_rows=" in line and _PROG["nexp"]:
        _PROG["rows"] += 1
        _PROG["sub"] = max(_PROG["sub"],
                           0.35 * min(1.0, _PROG["rows"] / _PROG["nexp"]))
    elif line.startswith("exporting "):
        _PROG["sub"] = max(_PROG["sub"], 0.6)
    elif m:
        _PROG["sub"] = max(_PROG["sub"], 0.6 + 0.4 * int(m[1]) / max(1, int(m[2])))
    return _prog_frac()


def _prog_solve(done, total):
    _PROG["sub"] = max(_PROG["sub"], 0.35 + 0.25 * done / max(1, total))
    return _prog_frac()


def pipeline(symbols, weeklies=False):
    """Download and export each ticker in turn (all held tickers if none are
    given).

    Each ticker is processed on its own, so one failure does not stop the rest.
    Returns (updated, failed): the updated symbols and {symbol: reason} for the
    others.
    """
    if not symbols:
        symbols = [h["symbol"] for h in archive.symbols()]
        if not symbols:
            raise RuntimeError("nothing held yet, type a ticker first")
    if not page_path().exists():
        build_shell()
    updated, failed = [], {}
    n = len(symbols)
    _prog_start(n)
    for i, sym in enumerate(symbols, 1):
        _prog_ticker(i)
        _STEP["text"] = f"{i}/{n} · " if n > 1 else ""
        try:
            print(f"downloading {sym}" + ("  (with weeklies)" if weeklies else ""))
            df = chain.enrich_many([sym], weeklies=weeklies)
            if df is None or not len(df):
                raise RuntimeError("no usable contracts")
            before = tickerfiles.held().get(sym)
            print(f"exporting {sym}")
            _run_script("charts/export_data.py", [sym])
            after = tickerfiles.held().get(sym)
            if after is None or after == before:
                # Unchanged export version: nothing passed the quality checks.
                raise RuntimeError("no strikes passed the quality checks")
            updated.append(sym)
        except Exception as e:
            failed[sym] = str(e)
            print(f"{sym}: failed ({e})")
    _STEP["text"] = ""
    return updated, failed


def closed_market_note(symbols):
    """Warning for tickers whose download fell outside regular trading hours.

    Empty when every chart rests on a download taken while the market was
    open and nothing newer was skipped.
    """
    bad, kept = [], []
    for sym in symbols:
        try:
            d = json.loads((sub("data") / "tickers" / f"{sym}.json")
                           .read_text(encoding="utf-8"))
        except Exception:
            continue
        a = d.get("archive") or {}
        if d.get("state") != "REGULAR":
            bad.append(sym)
        elif a.get("latest_state") not in (None, "REGULAR"):
            when = str(a.get("captured", ""))[:16].replace("T", " ")
            kept.append(f"{sym} {when}")
    parts = []
    if bad:
        parts.append(f"NOT RELIABLE: {', '.join(bad)} downloaded outside US "
                     "trading hours. Download again between 15:30 and 22:00 "
                     "CET.")
    if kept:
        parts.append("Market closed: the chart keeps the last download taken "
                     f"during trading hours ({', '.join(kept)}).")
    return "  ".join(parts)


class Api:
    """What the page can call. Names starting with _ are not exposed."""

    def __init__(self):
        self._window = None
        chain.PROGRESS = self._solve_progress
        self._busy = False
        self._lock = threading.Lock()

    # Called from the page

    def status(self):
        held = sorted(tickerfiles.held())
        note = (f"{len(held)} ticker{'s' if len(held) != 1 else ''} held  ·  "
                f"data in {home()}") if held else f"data in {home()}"
        alert = getattr(self, "_alert", "")
        return {"busy": self._busy, "held": held,
                "note": alert or note, "alert": bool(alert)}

    def refresh(self, symbols, weeklies=False, current=""):
        syms = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
        with self._lock:
            if self._busy:
                return {"ok": False, "msg": "already working, wait for it to finish"}
            self._busy = True
        focus = syms[0] if syms else (current or "")
        threading.Thread(target=self._work, args=(syms, bool(weeklies), focus),
                         daemon=True).start()
        return {"ok": True}

    def open_in_browser(self):
        p = page_path()
        if p.exists():
            webbrowser.open(p.as_uri())
        return True

    def open_data_folder(self):
        d = str(home())
        if sys.platform.startswith("win"):
            os.startfile(d)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["xdg-open", d])
        return True

    # Internal

    def _js(self, code):
        if self._window is not None:
            try:
                self._window.evaluate_js(code)
            except Exception:
                pass

    def _upgrade(self):
        """Re-export ticker files written by an older app version.

        Runs once when the window opens, from the chains already in the archive
        (only price history is fetched again), then reloads the chart.
        """
        todo = tickerfiles.stale()
        if not todo:
            return
        with self._lock:
            if self._busy:
                return
            self._busy = True
        focus = ""
        try:
            cur = self._window.get_current_url() or ""
            focus = cur.split("#", 1)[1] if "#" in cur else ""
        except Exception:
            pass
        done = 0
        with open(log_path(), "a", encoding="utf-8") as logf:
            saved = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = _Tee(logf, self._progress)
            try:
                print()
                print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] updating "
                      f"{' '.join(todo)}")
                _prog_start(len(todo), export_only=True)
                for i, sym in enumerate(todo, 1):
                    _prog_ticker(i)
                    _STEP["text"] = f"updating {i}/{len(todo)} · "
                    try:
                        print(f"{sym}: re-exporting with ten years of history")
                        _run_script("charts/export_data.py", [sym])
                        done += 1
                    except Exception as e:
                        print(f"{sym}: could not update ({e})")
            finally:
                _STEP["text"] = ""
                sys.stdout, sys.stderr = saved
        self._busy = False
        if done:
            self._show_page(focus)
        else:
            self._js("window.ocDone&&window.ocDone(false,'update of older tickers failed')")

    def _show_page(self, target):
        """Show the freshly built chart on the given ticker.

        If the chart is already showing, the page reloads itself: loading the
        same address again would only jump within the page, and pywebview's
        local file server does not accept a query string. From the welcome
        screen the address is loaded directly.
        """
        cur = ""
        try:
            cur = self._window.get_current_url() or ""
        except Exception:
            pass
        if "app.html" in cur:
            self._js("(function(t){try{if(t)history.replaceState(null,'','#'+t);}"
                     "catch(e){}location.reload();})(" + json.dumps(target) + ")")
        else:
            self._window.load_url(page_path().as_uri()
                                  + (f"#{target}" if target else ""))

    def _progress(self, line):
        frac = _prog_line(line)
        self._last = (_STEP["text"] + line)[:200]
        self._js(f"window.ocProgress&&window.ocProgress("
                 f"{json.dumps(self._last)},{frac:.4f})")

    def _solve_progress(self, done, total):
        frac = _prog_solve(done, total)
        self._js(f"window.ocProgress&&window.ocProgress("
                 f"{json.dumps(getattr(self, '_last', ''))},{frac:.4f})")

    def _work(self, syms, weeklies, focus):
        ok, msg = True, ""
        self._alert = ""
        with open(log_path(), "a", encoding="utf-8") as logf:
            tee = _Tee(logf, self._progress)
            saved = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = tee
            try:
                print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]")
                updated, failed = pipeline(syms, weeklies)
                if not updated:
                    ok = False
                    msg = "failed: " + "; ".join(f"{k} ({v})" for k, v in failed.items())
                else:
                    msg = f"done  ·  {len(updated)} updated"
                    if failed:
                        msg += "  ·  failed: " + ", ".join(failed)
                    if focus and focus not in updated:
                        focus = updated[0]
                    self._alert = closed_market_note(updated)
            except Exception as e:
                ok, msg = False, f"failed: {e}"
                traceback.print_exc()
            finally:
                sys.stdout, sys.stderr = saved
        self._busy = False
        if ok and page_path().exists() and self._window is not None:
            self._show_page(focus or "")
        else:
            self._js(f"window.ocDone&&window.ocDone({json.dumps(ok)},{json.dumps(msg)})")


# Shown before anything has been downloaded. It has the same controls and ids
# as the app bar in the chart page.
WELCOME = """<!doctype html><html><head><meta charset="utf-8">
<title>OptionsCone</title>
<style>
:root{--bg:#faf9f5;--panel:#fff;--ink:#12130f;--ink-2:#55564d;--ink-3:#8a8b80;--line:#e3e2d9;--line-2:#cfcec2}
@media (prefers-color-scheme:dark){:root{--bg:#15161a;--panel:#1c1e22;--ink:#f2f1ea;--ink-2:#b0b1a6;
  --ink-3:#7d7e74;--line:#2c2e33;--line-2:#3c3f45}}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,sans-serif}
.wrap{max-width:760px;margin:0 auto;padding:56px 16px}
h1{font-size:23px;font-weight:600;margin:0 0 8px}
p{color:var(--ink-2);margin:0 0 14px;max-width:62ch}
#appbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:26px 0 0;
  padding:12px;border:1px solid var(--line);border-radius:3px;background:var(--panel)}
input[type=text]{font:500 14px ui-monospace,monospace;padding:9px 10px;width:14ch;
  border:1px solid var(--line-2);border-radius:3px;background:var(--bg);color:var(--ink);text-transform:uppercase}
button{font:500 13px ui-monospace,monospace;padding:8px 13px;border:1px solid var(--line-2);
  background:transparent;color:var(--ink-2);border-radius:3px;cursor:pointer}
button:disabled{opacity:.45;cursor:default}
label{font-size:12.5px;color:var(--ink-2);display:flex;gap:5px;align-items:center}
#ab-status{font:12px ui-monospace,monospace;color:var(--ink-3);flex:1;min-width:20ch;margin-top:4px}
#ab-prog{width:160px;height:6px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:4px}
#ab-prog[hidden]{display:none}
#ab-prog i{display:block;height:100%;width:0;background:#3987e5;transition:width .25s ease}
.brk{flex-basis:100%;height:0}
.small{font-size:12px;color:var(--ink-3);margin-top:30px}
</style></head><body><div class="wrap">
<h1>OptionsCone</h1>
<p>The probability that a price touches, or finishes beyond, each listed strike before
expiry, from the option market and from a bootstrap of the stock's own history.</p>
<p>Type a ticker to download its option chain. The first download takes a minute or two.
Every download is archived on this computer, so a history builds up over time.</p>
<div id="appbar">
  <input type="text" id="ab-sym" placeholder="e.g. AAPL" spellcheck="false" autocomplete="off">
  <button id="ab-add">download</button>
  <button id="ab-all" style="display:none">refresh all</button>
  <label><input type="checkbox" id="ab-wk"> weeklies</label>
  <button id="ab-browser" data-keep="1" style="display:none">open in browser</button>
  <button id="ab-folder" data-keep="1">data folder</button>
  <span class="brk"></span>
  <span id="ab-prog" hidden><i></i></span>
  <span id="ab-status"></span>
</div>
<p class="small">Market data comes from Yahoo Finance through the yfinance library and is
fetched by this computer; you are responsible for complying with Yahoo's terms of use.
Quotes are only meaningful while the US market is open. Not financial advice.</p>
</div>
<script>
(function(){
  var bar=document.getElementById('appbar');
  var api=function(){return window.pywebview&&window.pywebview.api;};
  var st=document.getElementById('ab-status'), inp=document.getElementById('ab-sym'),
      wk=document.getElementById('ab-wk'), busy=false, wired=false;
  function setBusy(b){busy=b;
    bar.querySelectorAll('button').forEach(function(x){if(x.dataset.keep!=='1')x.disabled=b;});
    inp.disabled=b;}
  function go(list){ if(busy||!api())return; setBusy(true); st.textContent='starting...';
    api().refresh(list,wk.checked,'').then(function(r){
      if(!r||!r.ok){setBusy(false);st.textContent=(r&&r.msg)||'could not start';}});}
  function init(){ if(wired)return; wired=true;
    document.getElementById('ab-add').onclick=function(){
      var s=inp.value.split(/[ ,;]+/).filter(Boolean);
      if(!s.length){st.textContent='type a ticker first';inp.focus();return;} go(s);};
    inp.addEventListener('keydown',function(e){
      if(e.key==='Enter'){e.preventDefault();document.getElementById('ab-add').click();}});
    document.getElementById('ab-folder').onclick=function(){api().open_data_folder();};
    api().status().then(function(s){ if(s)st.textContent=s.note||''; });
    inp.focus();
  }
  var pb=document.getElementById('ab-prog'), pbi=pb.firstChild;
  window.ocProgress=function(line,frac){st.textContent=line;
    if(frac!=null){pb.hidden=false;pbi.style.width=(Math.max(0,Math.min(1,frac))*100).toFixed(1)+'%';}};
  window.ocDone=function(ok,msg){setBusy(false);st.textContent=msg;pb.hidden=true;};
  if(api())init(); else window.addEventListener('pywebviewready',init);
})();
</script></body></html>"""


def selftest(symbols):
    """Run the pipeline once without a window; the result goes to the log file
    and the exit code.
    """
    with open(log_path(), "a", encoding="utf-8") as logf:
        saved = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = _Tee(logf)
        try:
            print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] selftest, home={home()}")
            build_shell()
            updated, failed = pipeline(symbols, weeklies=False)
            held = tickerfiles.held()
            ok = (page_path().exists() and not failed
                  and all(s in held for s in symbols))
            print(f"SELFTEST {'OK' if ok else 'FAILED'}  updated={updated}  "
                  f"failed={failed}  held={sorted(held)}  page={page_path()}")
            return 0 if ok else 1
        except Exception:
            traceback.print_exc()
            print("SELFTEST FAILED")
            return 1
        finally:
            # Restore before the log closes, or the final flush fails.
            sys.stdout, sys.stderr = saved


def main():
    if "--selftest" in sys.argv:
        syms = [a.upper() for a in sys.argv[1:] if not a.startswith("--")] or ["AAPL"]
        return selftest(syms)

    import webview

    api = Api()
    try:
        build_shell()
    except Exception:
        with open(log_path(), "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
    p = page_path()
    if p.exists() and tickerfiles.held():
        win = webview.create_window(APP_NAME, url=p.as_uri(), js_api=api,
                                    width=1440, height=940, min_size=(900, 600))
    else:
        win = webview.create_window(APP_NAME, html=WELCOME, js_api=api,
                                    width=1100, height=760, min_size=(700, 500))
    api._window = win
    # Persistent profile, so settings kept in local storage survive a restart.
    webview.start(api._upgrade, private_mode=False,
                  storage_path=str(sub("webview")))
    return 0


if __name__ == "__main__":
    # Worker processes for the parallel solves start this program again; this
    # call hands such a start to the worker instead of opening a window.
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
