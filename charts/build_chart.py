"""Render the touch-probability surface as an HTML page."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from paths import sub  # noqa: E402

# Two builds of the same page. The all-in-one page (optionscone.html) carries
# every ticker inside it and works as a single file. The app shell (--app)
# carries none: it reads a small index of held tickers and loads a ticker's own
# file when it is selected, so a download rewrites only that file and the page
# itself never needs rebuilding.
APP = "--app" in sys.argv
DATA = {} if APP else json.loads((sub("data") / "surface_data.json").read_text())

HEAD = """<meta charset="utf-8">
<title>OptionsCone</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --bg:#faf9f5; --panel:#ffffff; --ink:#12130f; --ink-2:#55564d; --ink-3:#8a8b80;
  --line:#e3e2d9; --line-2:#cfcec2; --spot:#b8891f; --up:#3f6f4a; --dn:#a8443c;
  --q0:#f0f6fe; --p1:#cde2fb; --p2:#9ec5f4; --p3:#6da7ec; --p4:#3987e5; --p5:#256abf; --p6:#184f95; --p7:#0d366b;
  --on-light:#12130f; --on-dark:#ffffff; --warn-bg:#fdf3e0; --warn-ink:#7a5510; --warn-line:#e8cf9c;
  --bad-bg:#fdecea; --bad-ink:#8f1d16; --bad-line:#d9564b;
  --future:#f4f3ed; --track:#c2410c; --draw:#3f6f4a; --earn:#7c4bb8;
  --m5:#0f766e; --m10:#7c4bb8;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#15161a; --panel:#1c1e22; --ink:#f2f1ea; --ink-2:#b0b1a6; --ink-3:#7d7e74;
  --line:#2c2e33; --line-2:#3c3f45; --spot:#d6a53c; --up:#6aa87a; --dn:#d1706a;
  --q0:#0f1f33; --p1:#16304d; --p2:#1b4272; --p3:#20549a; --p4:#2a6ac0; --p5:#3987e5; --p6:#6da7ec; --p7:#9ec5f4;
  --on-light:#f2f1ea; --on-dark:#0b1220; --warn-bg:#2e2515; --warn-ink:#e8c887; --warn-line:#5c4a22;
  --bad-bg:#3a1714; --bad-ink:#ffb4ab; --bad-line:#b8453c;
  --future:#191b1f; --track:#fb923c; --draw:#6aa87a; --earn:#b08ce8;
  --m5:#2dd4bf; --m10:#c4a3f0;
}}
:root[data-theme="dark"]{
  --bg:#15161a; --panel:#1c1e22; --ink:#f2f1ea; --ink-2:#b0b1a6; --ink-3:#7d7e74;
  --line:#2c2e33; --line-2:#3c3f45; --spot:#d6a53c; --up:#6aa87a; --dn:#d1706a;
  --q0:#0f1f33; --p1:#16304d; --p2:#1b4272; --p3:#20549a; --p4:#2a6ac0; --p5:#3987e5; --p6:#6da7ec; --p7:#9ec5f4;
  --on-light:#f2f1ea; --on-dark:#0b1220; --warn-bg:#2e2515; --warn-ink:#e8c887; --warn-line:#5c4a22;
  --bad-bg:#3a1714; --bad-ink:#ffb4ab; --bad-line:#b8453c;
  --future:#191b1f; --track:#fb923c; --draw:#6aa87a; --earn:#b08ce8;
  --m5:#2dd4bf; --m10:#c4a3f0;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,-apple-system,sans-serif;
  font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1560px;margin:0 auto;padding-block:28px 56px;padding-left:16px;padding-right:16px}
h1{font-size:23px;font-weight:600;letter-spacing:-.015em;margin:0 0 6px;text-wrap:balance}
.sub{color:var(--ink-2);margin:0 0 22px;max-width:68ch;font-size:13.5px}
.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-variant-numeric:tabular-nums}
.bar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:16px}
.tabs{display:flex;gap:6px;flex-wrap:wrap}
.tsel{font:600 13px/1 "IBM Plex Mono",monospace;padding:8px 10px;
  border:1px solid var(--line-2);border-radius:3px;background:var(--panel);
  color:var(--ink);cursor:pointer}
.tsel:focus-visible{outline:2px solid var(--p4);outline-offset:2px}
.provenance{font-size:11px;color:var(--ink-3)}
.tab{font:500 13px/1 "IBM Plex Mono",monospace;letter-spacing:.03em;padding:9px 15px;border:1px solid var(--line-2);
  background:transparent;color:var(--ink-2);border-radius:3px;cursor:pointer}
.tab[aria-selected="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.tab:focus-visible,.zbtn:focus-visible{outline:2px solid var(--p4);outline-offset:2px}
.zoom{display:flex;gap:4px;align-items:center;margin-left:auto}
.zoom .lab{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);margin-right:4px}
.zbtn{font:500 12px/1 "IBM Plex Mono",monospace;padding:7px 11px;border:1px solid var(--line-2);
  background:transparent;color:var(--ink-2);border-radius:3px;cursor:pointer}
.zbtn[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
#md-[aria-pressed="true"]{background:var(--track);border-color:var(--track);color:#fff}
#md-mc5d[aria-pressed="true"]{background:var(--m5);border-color:var(--m5);color:#fff}
#md-mc10d[aria-pressed="true"]{background:var(--m10);border-color:var(--m10);color:#fff}
.bar.track{margin-top:-4px;padding-block:10px;border-top:1px dashed var(--line);
  border-bottom:1px dashed var(--line);margin-bottom:16px;
  flex-direction:column;align-items:stretch;gap:10px}
/* One row per group of controls: probability tracking, cone colouring, and the
   drawing tools with the moving averages. */
.trow{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.sep{width:1px;height:20px;background:var(--line-2);display:inline-block}
canvas.drawing{cursor:crosshair}
.sidelab{font:600 10px/1 "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink-3)}
.stepper{display:flex;align-items:center;gap:0;border:1px solid var(--line-2);border-radius:3px;overflow:hidden}
.stepper .zbtn.step{border:0;border-radius:0;padding:7px 13px;font-size:14px;line-height:1}
.stepper .zbtn.step:hover{background:var(--line)}
.pval{font:600 13px/1 "IBM Plex Mono",monospace;padding:0 12px;min-width:52px;text-align:center;
  color:var(--ink);font-variant-numeric:tabular-nums}
.provenance{font-size:11px;color:var(--ink-3)}
.trackout{font-size:11.5px;color:var(--ink-2);margin-left:auto;text-align:right;
  display:flex;flex-direction:column;gap:3px;align-items:flex-end}
.rline{display:flex;align-items:center;gap:6px;white-space:nowrap}
.ck{width:9px;height:9px;border-radius:50%;display:inline-block;flex:none}
.ck.solid{background:var(--track)}
.ck.hollow{background:transparent;border:1.5px solid var(--track)}
.trackout b{color:var(--track);font-weight:600}
/* The data table, the data quality report and the methods are sections of
   equal rank and share one bordered panel style. */
#tblbox,#dqbox,#methbox{margin:24px 0 0;border:1px solid var(--line);border-radius:3px;padding:12px 14px}
#tblbox summary,#dqbox summary,#methbox summary{font-weight:600;color:var(--ink);font-size:13.5px}
.meth{max-width:88ch;margin-top:6px}
.meth h3{font-size:13px;font-weight:600;color:var(--ink);margin:16px 0 4px}
.meth p{font-size:13px;line-height:1.55;color:var(--ink-2);margin:0}
.meth .small-note{margin-top:16px;font-size:12px;color:var(--ink-3)}
#dqout{margin-top:12px;font-size:12.5px;color:var(--ink-2)}
#dqout table{margin-top:8px}
.vgood{color:var(--up);font-weight:600}
.vfair{color:var(--ink);font-weight:600}
.vpoor,.vunusable{color:var(--dn);font-weight:600}
.pos{color:var(--up)} .neg{color:var(--dn)}
.warn{display:flex;gap:9px;align-items:flex-start;background:var(--warn-bg);border:1px solid var(--warn-line);
  color:var(--warn-ink);padding:10px 13px;border-radius:3px;font-size:12.5px;margin-bottom:18px}
.warn b{font-weight:600}
.warn.bad{background:var(--bad-bg);border:2px solid var(--bad-line);color:var(--bad-ink);
  font-size:14px;line-height:1.5;padding:13px 16px}
.warn.bad b:first-child{font-size:17px}
#ab-status.bad{color:var(--bad-ink);font-weight:600;white-space:normal}
.meta{display:flex;gap:26px;flex-wrap:wrap;margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--line)}
.meta div{display:flex;flex-direction:column;gap:3px}
.meta .k{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3)}
.meta .v{font-size:16px;font-weight:500}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:4px;overflow:hidden;
  display:flex;flex-direction:column}
/* Fullscreen takes the controls along into the panel, above the chart. */
.panel.fs{position:fixed;inset:0;z-index:60;border-radius:0;border:0;
  padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
.panel.fs .scroller{flex:1;min-height:0}
.panel.fs .fsbar{display:flex}
.fsbar{display:none;gap:14px;align-items:center;flex-wrap:wrap;
  padding:10px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
.fsbar .trackout{font-size:11px}
body.fslock{overflow:hidden}
.scroller{overflow-x:auto;overflow-y:hidden;scrollbar-width:none;-ms-overflow-style:none;
  cursor:grab}
.scroller::-webkit-scrollbar{display:none}
.scroller.grabbing{cursor:grabbing}
/* Clipped, so nothing positioned inside it (the hidden tooltip in particular)
   can stretch the scroll range past the chart. */
.stage{position:relative;overflow:hidden;width:max-content}
#cv{position:absolute;top:0;left:0}
canvas{display:block}
.legend{display:flex;align-items:center;gap:10px;padding:11px 14px;border-top:1px solid var(--line);flex-wrap:wrap}
.legend .lab{font-size:10.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3)}
.ramp{display:flex;align-items:center;gap:0}
.ramp i.grad{width:95px;height:13px;display:block;border-radius:2px;
  background:linear-gradient(90deg,var(--p1) 0%,var(--p2) 16.67%,var(--p3) 33.33%,
    var(--p4) 50%,var(--p5) 66.67%,var(--p6) 83.33%,var(--p7) 100%)}
.ramp i.grad{background-size:190px 100%}
.ramp i.grad.g2{background-position:-95px 0}
.star{display:inline-block;width:11px;height:11px;background:var(--earn);
  clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%)}
.dot{display:inline-block;border-radius:50%;width:7px;height:7px}
.dot.ink{background:var(--ink)}
.dot.hollow{background:var(--panel);border:1px solid var(--ink)}
.ramp .cap{font-size:11px;color:var(--ink-2);padding:0 7px}
.key{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--ink-2)}
.mln{width:16px;height:3px;border-radius:2px;display:inline-block}
.spotln{width:16px;height:0;border-top:2px dashed var(--spot);display:inline-block}
.swatch{width:11px;height:11px;border-radius:2px;display:inline-block}
.note{font-size:12px;color:var(--ink-3);margin-top:13px;max-width:80ch}
#tip{position:absolute;pointer-events:none;opacity:0;transition:opacity .09s;background:var(--ink);color:var(--bg);
  padding:7px 10px;border-radius:3px;font:500 11.5px/1.45 "IBM Plex Mono",monospace;white-space:pre;z-index:5;
  box-shadow:0 4px 14px rgba(0,0,0,.2)}
details{margin-top:20px;border-top:1px solid var(--line);padding-top:14px}
summary{cursor:pointer;font-size:12.5px;color:var(--ink-2);font-weight:500}
summary:focus-visible{outline:2px solid var(--p4);outline-offset:2px}
table{border-collapse:collapse;margin-top:12px;font-size:11.5px;width:100%}
th,td{text-align:right;padding:5px 9px;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{font-weight:600;color:var(--ink-2);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase}
tr.atm td{background:var(--line)}
@media (max-width:560px){.meta{gap:16px}.meta .v{font-size:14px}h1{font-size:19px}.zoom{margin-left:0}}
/* The desktop app's own controls, hidden in the all-in-one page, which has
   nothing to download with. */
#appbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:0 0 18px;
  padding:10px 12px;border:1px solid var(--line);border-radius:3px;background:var(--panel)}
#appbar[hidden]{display:none!important}
#appbar input[type=text]{font:500 13px/1 "IBM Plex Mono",monospace;padding:8px 10px;width:14ch;
  border:1px solid var(--line-2);border-radius:3px;background:var(--bg);color:var(--ink);text-transform:uppercase}
#appbar label{font-size:12px;color:var(--ink-2);display:flex;gap:5px;align-items:center}
#appbar .zbtn:disabled{opacity:.45;cursor:default}
#ab-status{font-size:11.5px;color:var(--ink-3);flex:1;min-width:20ch;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
#ab-prog{width:160px;height:6px;border-radius:3px;background:var(--line);overflow:hidden;flex:none}
#ab-prog[hidden]{display:none}
#ab-prog i{display:block;height:100%;width:0;background:var(--p4);transition:width .25s ease}
.zbtn.ema{display:inline-flex;align-items:center;gap:5px}
.zbtn.ema .sw{width:12px;height:3px;border-radius:2px;display:inline-block}
.eman{width:7.5ch;padding:6px 6px;border:1px solid var(--line-2);border-radius:3px;
  background:var(--panel);color:var(--ink);font-size:12px}
</style>
"""

BODY = """<div class="wrap">
<div id="appbar" hidden>
  <span class="lab">Ticker</span>
  <input type="text" id="ab-sym" placeholder="e.g. MSFT" spellcheck="false" autocomplete="off">
  <button class="zbtn" id="ab-add">download</button>
  <button class="zbtn" id="ab-all" title="Download a fresh chain for every ticker already held">refresh all</button>
  <label><input type="checkbox" id="ab-wk"> weeklies</label>
  <span class="sep"></span>
  <button class="zbtn" id="ab-browser" data-keep="1" title="Open this page in your web browser">open in browser</button>
  <button class="zbtn" id="ab-folder" data-keep="1" title="Where the archive and the page are stored">data folder</button>
  <span id="ab-prog" hidden><i></i></span>
  <span id="ab-status" class="mono"></span>
</div>
<h1>OptionsCone</h1>

<div class="bar">
  <span class="lab">Ticker</span>
  <select id="tsel" class="tsel"></select>
  <span class="provenance mono" id="prov"></span>
  <div class="zoom">
    <span class="lab">Bars</span>
    <button class="zbtn" id="bar-d" aria-pressed="true">daily</button>
    <button class="zbtn" id="bar-w" aria-pressed="false">weekly</button>
    <span class="lab" style="margin-left:14px">Zoom</span>
    <button class="zbtn" id="yreset" title="Ctrl or Shift + scroll wheel over the chart to zoom">reset <span id="yz" class="mono">fit</span></button>
  </div>
</div>

<div id="trackhome"><div class="bar track">
 <div class="trow">
  <span class="lab">Track probability</span>
  <span class="sidelab dn">down</span>
  <div class="stepper">
    <button class="zbtn step" id="pdn-" aria-label="Lower the downside probability">&minus;</button>
    <output class="pval mono" id="pvaldn">30%</output>
    <button class="zbtn step" id="pdn+" aria-label="Raise the downside probability">+</button>
  </div>
  <span class="sidelab up">up</span>
  <div class="stepper">
    <button class="zbtn step" id="pup-" aria-label="Lower the upside probability">&minus;</button>
    <output class="pval mono" id="pvalup">30%</output>
    <button class="zbtn step" id="pup+" aria-label="Raise the upside probability">+</button>
  </div>
  <button class="zbtn" id="plink" aria-pressed="true" title="Move both sides together">linked</button>
  <span class="sep"></span>
  <span class="lab">Contour</span>
  <button class="zbtn" id="ck-p" aria-pressed="true" title="Probability of touching the strike at any point">touch</button>
  <button class="zbtn" id="ck-pexp" aria-pressed="false" title="Probability of finishing beyond the strike">expire</button>
  <span class="sep"></span>
  <span class="lab">Models</span>
  <button class="zbtn mdl" id="md-" aria-pressed="true" title="From the option prices">implied</button>
  <button class="zbtn mdl" id="md-mc5d" aria-pressed="true" title="Bootstrap of the last five years, realised drift kept">5y</button>
  <button class="zbtn mdl" id="md-mc10d" aria-pressed="true" title="Bootstrap of the last ten years, realised drift kept">10y</button>
  <span class="trackout mono" id="trackout"></span>
 </div>
 <div class="trow">
  <span class="lab">Cone</span>
  <button class="zbtn" id="cm-p" aria-pressed="true">probability</button>
  <button class="zbtn" id="cm-iv" aria-pressed="false">IV</button>
  <button class="zbtn" id="cm-oi" aria-pressed="false">open int.</button>
  <button class="zbtn" id="cm-spr" aria-pressed="false">spread</button>
  <span class="sep"></span>
  <button class="zbtn" id="dots" aria-pressed="true" title="Show or hide the contract markers">dots</button>
  <button class="zbtn" id="fs" title="Fill the window (Esc or F to leave)">fullscreen</button>
 </div>
 <div class="trow">
  <span class="lab">Draw</span>
  <button class="zbtn" id="tool-none" aria-pressed="true" title="No drawing tool: the pointer hovers dots again (V)">off</button>
  <button class="zbtn" id="tool-tl" aria-pressed="false" title="Trend line (T): drag from one point to another">trend</button>
  <button class="zbtn" id="tool-hl" aria-pressed="false" title="Horizontal line (H): click a price level">horizontal</button>
  <button class="zbtn" id="clear-draw" title="Remove every drawing">clear</button>
  <span class="sep"></span>
  <span class="lab">EMA</span>
  <button class="zbtn ema" id="ema0" aria-pressed="false" title="Exponential moving average of the close"><i class="sw" style="background:#0891b2"></i>1</button>
  <input class="eman mono" id="ema0n" type="number" min="2" max="1000" step="1" value="20" title="Trading days">
  <button class="zbtn ema" id="ema1" aria-pressed="false" title="Exponential moving average of the close"><i class="sw" style="background:#db2777"></i>2</button>
  <input class="eman mono" id="ema1n" type="number" min="2" max="1000" step="1" value="50" title="Trading days">
 </div>
</div></div>



<div id="warn"></div>
<div class="meta" id="meta"></div>

<div class="panel" id="panel">
  <div class="fsbar" id="fsbar"></div>
  <div class="scroller" id="scroller">
    <div class="stage" id="stage">
      <canvas id="cv"></canvas>
      <div id="tip"></div>
    </div>
  </div>
  <div class="legend" id="legendbar">
    <span class="lab" id="fieldlab">P(touch) &middot; implied</span>
    <span class="ramp">
      <span class="cap" id="capLo">0</span>
      <i class="grad"></i>
      <span class="cap" id="capMid">50</span>
      <i class="grad g2"></i>
      <span class="cap" id="capHi">100%</span>
    </span>
    <span class="key"><span class="dot ink"></span>listed contract</span>
    <span class="key"><span class="star"></span>earnings</span>
    <span class="key"><span class="mln" style="background:var(--track)"></span>implied</span>
    <span class="key"><span class="mln" style="background:var(--m5)"></span>5y bootstrap</span>
    <span class="key"><span class="mln" style="background:var(--m10)"></span>10y bootstrap</span>
    <span class="key" style="margin-left:auto"><span class="spotln"></span>spot</span>
  </div>
</div>




<details id="tblbox">
  <summary>Data table</summary>
  <div class="bar" style="margin:12px 0 0">
    <span class="lab">Show</span>
    <button class="zbtn" id="tb-cone" aria-pressed="true" title="The same values the cone is coloured by">cone colouring</button>
    <button class="zbtn" id="tb-delta" aria-pressed="false" title="Each contract's delta: calls above spot, puts below">delta</button>
  </div>
  <div id="tbl"></div>
</details>

<details id="dqbox">
  <summary>Data quality: what these numbers rest on</summary>
  <div id="dqout"></div>
</details>

<details id="methbox">
  <summary>Methods</summary>
  <div class="meth">
  <h3>Data</h3>
  <p>Option chains, prices and earnings dates come from Yahoo Finance through the yfinance library, fetched by this computer. Option quotes are delayed by about 15 minutes. Every download is archived; the chart uses the newest download taken while the US market was open. The risk-free rate is the 13-week US Treasury bill yield (^IRX). Future dividends are projected from the payout history: the last payment is carried forward at the observed frequency.</p>

  <h3>Which contracts are used</h3>
  <p>Contracts expiring within 10 days are dropped, as are contracts with an absolute delta below 0.05. Hard checks remove impossible quotes: no bid or no ask, ask below bid, a mid below one cent, a price below intrinsic value or above its theoretical cap, and an implied volatility outside 1% to 300%. Soft checks flag doubtful quotes without removing them: a spread above 25% of the mid, a bid of one cent, a put-call parity error beyond the half spread, an inconsistent forward, and thin open interest. Calls are used above spot and puts below, so every contract on the chart is out of the money.</p>

  <h3>Implied volatility and Greeks</h3>
  <p>Each contract's volatility is solved from the bid-ask mid with an American binomial tree (Cox-Ross-Rubinstein, 160 steps), using Brent root finding. Dividends enter by the escrowed-dividend method. Delta and gamma are central differences on the same tree, shifting spot by 1%. A contract whose quote fails the price checks takes the volatility of the nearest strike that passes; its dot is drawn hollow. Open interest does not decide this.</p>

  <h3>Implied probabilities</h3>
  <p>Touch is the probability that the price reaches the strike at any time before expiry, from the closed form for a lognormal price with the contract's own volatility. Expire is the probability of finishing beyond the strike, N(d2). Both use the same risk-neutral assumptions: the price drifts at the risk-free rate. Expire is not delta: delta is N(d1), and the two differ by the volatility over the time left, which is a wide gap on volatile stocks.</p>

  <h3>Bootstrap models (5y, 10y)</h3>
  <p>Paths are built from the stock's own daily returns over the last 5 or 10 years. Blocks of 20 consecutive trading days are drawn with replacement and joined until the horizon is covered, so fat tails and runs of volatile days are kept. The realised drift is kept. Each simulated day carries the high and low of the real day it came from, so a touch is observed on the intraday range rather than inferred from closes. 10,000 paths per window. Touch is the share of paths whose low (high) reaches the strike by expiry; expire is the share whose final close is beyond it. These are historical frequencies, not option-market prices, and they only contain moves that happened in the sample.</p>

  <h3>Expiry badges</h3>
  <p>The badge above each expiry is its model-free implied volatility: the VIX variance-swap replication applied to that expiry alone, using out-of-the-money quotes weighted by dK/K&sup2;, the forward from put-call parity near the money, and a stop after two consecutive zero bids. The ratio below it divides that volatility by realized volatility.</p>

  <h3>Realized Vola</h3>
  <p>Close-to-close volatility over the last year, exponentially weighted with a 6-week half-life and annualised with 252 trading days.</p>

  <h3>The cone</h3>
  <p>Probability colouring is interpolated between the listed strikes and expiries, in log price. Where an expiry does not list a strike, the probability is computed from the volatility of its nearest listed strike, so the field stays continuous; no dot is drawn there. IV, open interest and spread are painted outward from each contract, each point taking the strongest nearby contract, and fade out beyond the outermost listed strikes. Probability uses a fixed 0 to 100% scale; IV a linear scale over the values shown; open interest and spread a logarithmic scale, with spread inverted so that darker means tighter.</p>

  <h3>Contours</h3>
  <p>For each expiry and model, the contour marks the listed strike whose probability is closest to the target, separately above and below spot. A filled marker is within 5 percentage points of the target, a hollow one is the nearest available but further off.</p>

  <h3>EMA</h3>
  <p>Exponential moving average of the close, seeded with a simple average over the first period and computed over the whole history. The period is in trading days; on weekly bars it is divided by five.</p>

  <p class="small-note">All probabilities are estimates from market prices or from the past. They are not forecasts and not financial advice.</p>
  </div>
</details>
</div>
"""

SCRIPT = r"""<script>
const RAMP=['--p1','--p2','--p3','--p4','--p5','--p6','--p7'];
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
// The whole exported history (ten years) is always on the chart; the view is
// moved by dragging and zooming.
let cur=Object.keys(DATA)[0], barMode='d';
// Vertical offset of the price window, as a fraction of its height. The range
// still fits what is on screen; this slides it up or down, so a cone cut off
// at the top or bottom can be dragged into view.
let yShift=0;
// Two exponential moving averages of the close, periods in trading days.
let EMAS=[{on:false,n:20,col:'#0891b2'},{on:false,n:50,col:'#db2777'}];
try{const _e=JSON.parse(localStorage.getItem('oc_ema')||'null');
  if(Array.isArray(_e))_e.forEach((v,i)=>{if(EMAS[i]&&v){EMAS[i].on=!!v.on;
    if(v.n>=2&&v.n<=1000)EMAS[i].n=Math.round(v.n);}});}catch(e){}
let trackDn=0.30, trackUp=0.30, trackOn=true;  // one contour per side
// A terminal probability cannot exceed one half on either side of spot: the
// strike nearest the money is the likeliest to finish beyond, and that is a
// coin flip. Beyond that the match would pick a strike on the wrong side, so
// the expire contour is not drawn.
const PEXP_MAX=0.50;
// Which probability the contours track (touch or terminal), and which models
// are drawn.
let contourKind='p';          // 'p' = touched at any point, 'pexp' = finished beyond
const MODELS=[
  {key:'',     label:'implied', col:'--track'},
  {key:'mc5d', label:'5y',      col:'--m5'},
  {key:'mc10d',label:'10y',     col:'--m10'}
];
let modelOn={'':true,'mc5d':true,'mc10d':true};
const fieldOf=(m,kind)=>kind==='p'?(m||'p'):(m?m+'exp':'pexp');
let linked=true;
const PADL=54,PADR=18,PADT=16,AXISH=30,IVH=58;
let PLOTH=820;
const day=t=>Math.round(new Date(t+'T00:00:00Z').getTime()/864e5);
// The x axis counts sessions, not calendar days, so a weekend takes no width
// and the candles sit next to each other. Future dates (the expiries) are
// placed by counting weekdays from the last bar.
let _sess=null;
function sessions(bars){
  if(_sess&&_sess.key===bars.length+':'+bars[0].t+':'+bars[bars.length-1].t)
    return _sess;
  const ix={}; bars.forEach((b,i)=>{ix[day(b.t)]=i;});
  const lastDay=day(bars[bars.length-1].t);
  _sess={key:bars.length+':'+bars[0].t+':'+bars[bars.length-1].t,
         ix:ix, n:bars.length, lastDay:lastDay};
  return _sess;
}
function slotOf(dd,S){
  if(S.ix[dd]!==undefined)return S.ix[dd];
  if(dd<=S.lastDay){  // a gap inside the history: nearest session
    let k=dd; while(k>=S.lastDay-4000&&S.ix[k]===undefined)k--;
    return S.ix[k]!==undefined?S.ix[k]:0;
  }
  // Ahead of the last bar: count weekdays.
  let n=0;
  for(let k=S.lastDay+1;k<=dd;k++){
    const w=new Date(k*864e5).getUTCDay();
    if(w!==0&&w!==6)n++;
  }
  return S.n-1+n;
}
const CW_FIT=9;  // px per calendar day at zoom 1
// The lower limit is far below the opening zoom, so years of history fit on
// one screen.
const ZOOM_MIN=0.03, ZOOM_MAX=14, ZOOM_HOME=0.35;
// Drawings are stored in data coordinates (day number and price), so they stay
// pinned to the chart through zoom and scroll. Each render publishes the
// inverse of the draw transform to map the pointer back. `pending` is a trend
// line being dragged; `ghost` is a horizontal level following the pointer
// before it is placed.
let tool='none', drawings=[], pending=null, ghost=null;
// What the cone is coloured by. All four fields share one blue ramp, pale for
// low and dark for high. Probability has an absolute scale; the others are
// stretched across what is on screen, and the legend gives the values at each
// end.
let colourBy='p';
// The dots can be hidden to read the field on its own; with hundreds of ladder
// rows they crowd into solid lines.
let showDots=true;
// Scale per field. Open interest and spread span orders of magnitude, so they
// are coloured on a log scale: a doubling is the step that matters, and a
// linear scale would push most of the surface into one end of the ramp.
// Implied volatility is a rate with a narrow range across one chain and stays
// linear.
//
// `invert` flips a field so that dark always marks the favourable end: the
// tightest spread is the darkest cell.
const COLOUR={
  p:  {label:'probability', field:c=>c.p, scale:'lin', fmt:v=>(v*100).toFixed(0)+'%'},
  iv: {label:'implied vol', field:c=>c.iv, scale:'lin', clip:false, fmt:v=>(v*100).toFixed(1)+'%'},
  oi: {label:'open interest', field:c=>c.oi, scale:'log', clip:false, fmt:v=>Math.round(v).toLocaleString('en-US')},
  spr:{label:'spread', field:c=>c.spr, scale:'log', clip:false, invert:true, fmt:v=>(v*100).toFixed(1)+'%'}
};
// Values at or below zero cannot be logged and are left uncoloured rather than
// clamped: an open interest of zero is an absence, not a small amount.
const scaleOf=v=>{
  const sc=COLOUR[colourBy].scale;
  if(sc==='log')return v>0?Math.log(v):null;
  return v;
};
// Back out of scale space for the legend captions.
const unscale=t=>{
  const sc=COLOUR[colourBy].scale;
  if(sc==='log')return Math.exp(t);
  return t;
};
const val=(c,f)=>{
  if(f)return c[f]==null?c.p:c[f];
  // A synthetic cell has no contract, so on the open-interest and spread maps
  // it has no value; the field is interpolated across it from the listed
  // strikes either side, and nothing is extrapolated beyond them.
  if(c.synthetic&&colourBy!=='p'&&colourBy!=='iv')return null;
  const v=COLOUR[colourBy].field(c);
  return (v==null||!isFinite(v))?null:v;
};
const cellAt=(e,k)=>{
  if(!e._ix){e._ix={};e.cells.forEach(c=>{e._ix[c.k]=c;});}
  return e._ix[k]||null;
};
// The opening zoom shows the whole term structure at once.
let zoom=ZOOM_HOME, yCenter=null, yStretch=1;

// Continuous colour. The control points run from a pale stop to deep blue, and
// the ramp is re-parameterised so that perceived lightness (L*) falls linearly
// with probability: equal steps in probability are equal steps to the eye.
const RAMP_HEX=['--q0','--p1','--p2','--p3','--p4','--p5','--p6','--p7'];
let _ramp=null,_lut=null;
const hex2rgb=h=>{h=h.replace('#','');
  if(h.length===3)h=h.split('').map(c=>c+c).join('');
  return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];};
function rampStops(){return RAMP_HEX.map(n=>hex2rgb(css(n)));}
function _raw(t){
  const u=Math.min(1,Math.max(0,t))*(_ramp.length-1);
  const i=Math.min(_ramp.length-2,Math.floor(u)), f=u-i;
  const a=_ramp[i], b=_ramp[i+1];
  return [a[0]+(b[0]-a[0])*f, a[1]+(b[1]-a[1])*f, a[2]+(b[2]-a[2])*f];
}
const _lin=c=>{c/=255;return c<=0.04045?c/12.92:Math.pow((c+0.055)/1.055,2.4);};
function _Lstar(c){
  const y=0.2126*_lin(c[0])+0.7152*_lin(c[1])+0.0722*_lin(c[2]);
  return y<=0.008856?903.3*y:116*Math.pow(y,1/3)-16;
}
function buildLut(){  // 256 entries, even in perceived lightness
  _ramp=rampStops();
  const L0=_Lstar(_raw(0)), L1=_Lstar(_raw(1));
  _lut=new Uint8Array(256*3);
  for(let k=0;k<256;k++){
    const want=L0+(L1-L0)*(k/255);
    let lo=0,hi=1;
    for(let it=0;it<24;it++){const m=(lo+hi)/2;if(_Lstar(_raw(m))>want)lo=m;else hi=m;}
    const c=_raw((lo+hi)/2);
    _lut[k*3]=c[0];_lut[k*3+1]=c[1];_lut[k*3+2]=c[2];
  }
}

function lutIdx(p){return Math.min(255,Math.max(0,Math.round(p*255)));}
function probColor(p,alpha){
  if(!_lut)buildLut();
  const k=lutIdx(p)*3;
  return 'rgba('+_lut[k]+','+_lut[k+1]+','+_lut[k+2]+','+(alpha===undefined?1:alpha)+')';
}

// Which download the chart shows. Later downloads taken outside trading hours
// are archived but not used, and the line says so.
function provText(a){
  if(!a)return '';
  const t=s=>s.replace('T',' ').slice(0,16);
  let s='captured '+t(a.captured)+'  ·  '+a.n_pulls+' pull'+(a.n_pulls>1?'s':'')+' archived';
  if(a.latest&&a.latest!==a.captured&&a.latest_state&&a.latest_state!=='REGULAR')
    s+='  ·  newer download from '+t(a.latest)+' not used (outside trading hours)';
  return s;
}

function build(){
  if(!DATA[cur])return;  // app shell: data not loaded yet
  const d=DATA[cur];
  document.querySelectorAll('.tab').forEach(t=>t.setAttribute('aria-selected',t.dataset.k===cur));
  // No download of this ticker was taken during regular trading hours, so the
  // chart rests on placeholder quotes. Said loudly, above the chart.
  const _when={PRE:'before the US market opened',PREPRE:'before the US market opened',
    POST:'after the US market closed',POSTPOST:'after the US market closed',
    CLOSED:'while the US market was closed'}[d.state]||'outside regular US trading hours';
  const _cap=d.archive&&d.archive.captured?' ('+d.archive.captured.replace('T',' ').slice(0,16)+')':'';
  document.getElementById('warn').innerHTML = d.state!=='REGULAR'
    ? '<div class="warn bad"><b>&#9888;</b><span><b>Not reliable.</b> These quotes were downloaded '+
      _when+_cap+'. Outside trading hours the option feed returns placeholder prices, '+
      'so the probabilities, volatilities and spreads below can be badly wrong. '+
      '<b>Download '+cur+' again during US trading hours</b>: 9:30 to 16:00 New York time, '+
      'usually 15:30 to 22:00 in Central Europe.</span></div>' : '';
  document.getElementById('meta').innerHTML=[
    ['Spot',d.spot.toFixed(2)],['As of',d.asof],['Contracts',d.n],
    ['Realized Vola',(d.rv.ewma.sigma*100).toFixed(1)+'%'],
    ['Contracts passing checks',(d.n_clean!=null?d.n_clean+' / '+d.n:
        d.clean_pct.toFixed(0)+'%')]
  ].map(([k,v])=>'<div><span class="k">'+k+'</span><span class="v mono">'+v+'</span></div>').join('');
  draw();table();legend();readout();dqRender();
  const pv=document.getElementById('prov');
  if(pv)pv.textContent=provText(d.archive);
  const fl=document.getElementById('fieldlab');
  if(fl)fl.textContent=COLOUR[colourBy].label;
  // Jump to the latest bars and draw again, so the price range fits the bars
  // now on screen.
  document.getElementById('scroller').scrollLeft=1e6;
  draw();
}

// For each expiry, the listed strike whose probability is closest to the
// target, separately above and below spot. Returns the cell itself, so the
// readout names a real contract.
function trackedStrikes(d,target,field,up){
  field=field||'p';
  const out=[];
  d.expiries.forEach(e=>{
    let best=null,bd=Infinity;
    e.cells.forEach(c=>{
      // Synthetic cells carry a probability for the field only; no contract
      // sits there, so they are skipped.
      if(c.synthetic)return;
      if(c.up!==up)return;
      const v=c[field]; if(v==null)return;
      const dist=Math.abs(v-target);
      if(dist<bd){bd=dist;best=c;}
    });
    // Beyond the ends of the ladder the nearest strike can be far from the
    // target; it is kept but marked.
    if(best&&bd<=0.25)out.push({e:e,c:best,up:up,miss:bd,near:bd<=0.05});
  });
  return out;
}

// The ramp's captions. Probability runs from 0 to 100%; the other fields are
// stretched across what is on screen, so the ends report the values actually
// there, converted back from log space.
function legendCaps(vlo,vhi){
  const C=COLOUR[colourBy], inv=unscale;
  const lo=document.getElementById('capLo'),
        mid=document.getElementById('capMid'),
        hi=document.getElementById('capHi');
  if(!lo||!mid||!hi)return;
  if(colourBy==='p'){lo.textContent='0';mid.textContent='50';hi.textContent='100%';return;}
  // The ramp always runs pale to dark from left to right. For an inverted
  // field the pale end is the largest value, so the captions run the other
  // way.
  const a=C.fmt(inv(vlo)), b=C.fmt(inv((vlo+vhi)/2)), c=C.fmt(inv(vhi));
  if(C.invert===true){lo.textContent=c;mid.textContent=b;hi.textContent=a;}
  else {lo.textContent=a;mid.textContent=b;hi.textContent=c;}
}

function legend(){
  if(!_lut)buildLut();
  const stops=[];
  for(let i=0;i<=10;i++){
    const k=lutIdx(i/10)*3;
    stops.push('rgb('+_lut[k]+','+_lut[k+1]+','+_lut[k+2]+') '+(i*10)+'%');}
  const g='linear-gradient(90deg,'+stops.join(',')+')';
  document.querySelectorAll('.ramp i.grad').forEach((el,i)=>{
    el.style.background=g;el.style.backgroundSize='190px 100%';
    el.style.backgroundPosition=(i?'-95px':'0')+' 0';});
}

function draw(){
  if(!DATA[cur])return;  // app shell: data not loaded yet
  const d=DATA[cur];
  const src=barMode==='w'?(d.ohlcw||d.ohlc):d.ohlc;
  const bars=src.slice(), exps=d.expiries, rows=d.rows;
  const cv=document.getElementById('cv'),ctx=cv.getContext('2d');

  // One calendar scale for candles and grid: x is a day number, so an expiry
  // column lands on its real date.
  const SESS=sessions(bars);
  const slotLast=slotOf(day(exps[exps.length-1].expiry),SESS);
  const dNow=day(bars[bars.length-1].t);
  const span=slotLast+8;
  window._geom={span:span};
  const CW=CW_FIT*zoom;
  // At least about 60 px after the last expiry at any zoom, so the right edge
  // reads as the end of the chart.
  const W=PADL+span*CW+PADR+Math.max(0,60-6*CW), H=PADT+IVH+PLOTH+AXISH;
  const dpr=window.devicePixelRatio||1;
  // The timeline can be over a hundred thousand pixels wide, but browsers draw
  // nothing on a canvas much over 32,000. So the stage carries the full width
  // for scrolling, and the canvas is only the visible window, moved to the
  // scroll position. Everything is drawn in timeline coordinates; the
  // transform shifts it into the window and the rest is clipped.
  const stg=document.getElementById('stage'), scr=document.getElementById('scroller');
  stg.style.width=W+'px'; stg.style.height=H+'px';
  const VW=Math.max(1,Math.min(W,(scr&&scr.clientWidth)||1000));
  const VL=Math.max(0,Math.min((scr&&scr.scrollLeft)||0,W-VW));
  cv.style.left=VL+'px';
  cv.width=Math.round(VW*dpr);cv.height=Math.round(H*dpr);
  cv.style.width=VW+'px';cv.style.height=H+'px';
  ctx.setTransform(dpr,0,0,dpr,-VL*dpr,0);ctx.clearRect(VL,0,VW,H);
  const x=t=>PADL+(slotOf(t,SESS)+2)*CW;

  // The price axis fits what is on screen: the visible candles set the range,
  // padded a little, and the strike ladder counts only as far as the drawn
  // cone reaches.
  const viewL=VL, viewW=VW;
  const sFrom=(viewL-PADL)/CW-2, sTo=(viewL+viewW-PADL)/CW-2;
  const slotDay=sl=>{  // slot -> calendar day, for filters
    if(sl<0)return day(bars[0].t)+Math.round(sl*1.4);
    if(sl<bars.length)return day(bars[Math.floor(sl)].t);
    return SESS.lastDay+Math.round((sl-bars.length+1)*1.4);
  };
  const dFrom=slotDay(sFrom), dTo=slotDay(sTo);
  const vis=bars.filter((b,i)=>i>=sFrom-1&&i<=sTo+1);
  const seen=vis.length?vis:bars.slice(-40);
  let fLo=Math.min(...seen.map(b=>b.l)), fHi=Math.max(...seen.map(b=>b.h));
  // Any expiry column inside the view brings its drawn strikes with it, so the
  // cone is not cropped by a range fitted to the candles alone.
  exps.forEach(e=>{
    const q=day(e.expiry);
    if(q<dFrom-2||q>dTo+2)return;
    // The price range follows the probability cone whichever field is
    // coloured, so switching the colour never changes the vertical extent.
    e.cells.forEach(c=>{if((c.p||0)>=0.04){fLo=Math.min(fLo,c.k);fHi=Math.max(fHi,c.k);}});
  });
  if(dTo>=day(exps[0].expiry)-2)fHi=Math.max(fHi,d.spot);
  const fPad=(fHi-fLo)*0.06;fLo-=fPad;fHi+=fPad;
  if(yCenter===null)yCenter=(fLo+fHi)/2;
  const fullSpan=fHi-fLo, ySpan=fullSpan/yStretch;
  let lo=yCenter-ySpan/2, hi=yCenter+ySpan/2;
  if(yStretch===1){lo=fLo;hi=fHi;}
  {const _sh=(hi-lo)*yShift; lo+=_sh; hi+=_sh;}
  window._ydom={lo:lo,hi:hi,fLo:fLo,fHi:fHi};
  const TOP=PADT+IVH;
  const y=v=>TOP+PLOTH-(v-lo)/(hi-lo)*PLOTH;

  const ink2=css('--ink-2'),ink3=css('--ink-3'),line=css('--line'),line2=css('--line-2'),
        spotc=css('--spot'),up=css('--up'),dn=css('--dn'),panel=css('--panel');

  // Price ladder: the finest increment whose labels still clear each other at
  // the current zoom.
  const STEPS=[1,2,2.5,5,10,20,25,50,100];
  const pxPer=PLOTH/(hi-lo);
  const major=STEPS.find(st=>st*pxPer>=15)||100;
  const minor=STEPS.find(st=>st*pxPer>=4.5)||1;
  ctx.textBaseline='middle';ctx.lineWidth=1;

  // Price levels are marked on the axis only; grid lines across the plot would
  // compete with the probability field.
  ctx.font='11px "IBM Plex Mono",monospace';
  const ticks=[];
  for(let v=Math.ceil(lo/major)*major;v<hi;v+=major)
    ticks.push([v,Math.round(y(v))+.5]);


  // Candles
  const bw=Math.max(1,CW-3);
  bars.forEach(b=>{
    const cx=Math.round(x(day(b.t)))+.5, rise=b.c>=b.o, col=rise?up:dn;
    ctx.strokeStyle=col;ctx.fillStyle=col;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(cx,y(b.h));ctx.lineTo(cx,y(b.l));ctx.stroke();
    const yo=y(b.o),yc=y(b.c),top=Math.min(yo,yc),h=Math.max(1,Math.abs(yc-yo));
    ctx.fillRect(cx-bw/2,top,bw,h);  // both directions solid
  });

  // Moving averages, computed over the whole series so they are settled before
  // the first visible bar. The period is in trading days; on weekly bars it is
  // converted to weeks.
  EMAS.forEach(E=>{
    if(!E.on)return;
    const span=barMode==='w'?Math.max(1,Math.round(E.n/5)):E.n;
    if(src.length<span)return;
    const a=2/(span+1), off=src.length-bars.length;
    let v=0; for(let i=0;i<span;i++)v+=src[i].c; v/=span;  // seeded with the SMA
    const val=new Array(src.length).fill(null); val[span-1]=v;
    for(let i=span;i<src.length;i++){v=a*src[i].c+(1-a)*v;val[i]=v;}
    ctx.strokeStyle=E.col;ctx.lineWidth=1.6;ctx.beginPath();
    let pen=false;
    bars.forEach((b,j)=>{const q=val[j+off];
      if(q==null){pen=false;return;}
      const px=Math.round(x(day(b.t)))+.5, py=y(q);
      if(pen)ctx.lineTo(px,py);else{ctx.moveTo(px,py);pen=true;}});
    ctx.stroke();
  });

  // Spot reference
  ctx.strokeStyle=spotc;ctx.lineWidth=1.4;ctx.setLineDash([5,4]);
  ctx.beginPath();ctx.moveTo(PADL,Math.round(y(d.spot))+.5);ctx.lineTo(W-PADR,Math.round(y(d.spot))+.5);ctx.stroke();
  ctx.setLineDash([]);
  // Today
  ctx.strokeStyle=ink3;ctx.lineWidth=1;ctx.setLineDash([3,3]);
  ctx.beginPath();ctx.moveTo(Math.round(x(dNow)+CW/2)+.5,TOP);ctx.lineTo(Math.round(x(dNow)+CW/2)+.5,TOP+PLOTH);ctx.stroke();
  ctx.setLineDash([]);

  // Alpha is held flat across the field so that perceived lightness follows
  // the colour ramp alone. Only the lowest probabilities fade, over a short
  // interval, so the cone dissolves into the page instead of ending on a hard
  // edge.
  const alphaAt=p=>p>=0.06?232:Math.round(232*(p/0.06));

  // The probability field, drawn as a continuous raster before the dots.
  // Values are bilinear between the lattice of listed strikes and expiries,
  // and alpha falls to zero before the first expiry so the cone grows out of
  // today.
  {
    const gx0=x(dNow), gx1=x(day(exps[exps.length-1].expiry));
    const kLo=rows[0], kHi=rows[rows.length-1];
    const gy0=y(kHi), gy1=y(kLo);
    // Only the part of the field inside the visible window is computed.
    const wFull=Math.max(2,Math.round(gx1-gx0)), hFull=Math.max(2,Math.round(gy1-gy0));
    // The field starts just past the right edge of the last candle, so it
    // never covers the latest bar.
    const vx0=Math.max(gx0+bw/2+2,viewL), vx1=Math.min(gx1,viewL+viewW);
    const vy0=Math.max(gy0,TOP), vy1=Math.min(gy1,TOP+PLOTH);
    const ixOff=Math.round(vx0-gx0), iyOff=Math.round(vy0-gy0);
    const wpx=Math.max(1,Math.round(vx1-vx0)), hpx=Math.max(1,Math.round(vy1-vy0));
    if(wpx>1&&hpx>1&&wpx*hpx<4.2e6){
      const off=document.createElement('canvas');
      off.width=wpx;off.height=hpx;
      const octx=off.getContext('2d');
      const img=octx.createImageData(wpx,hpx), px=img.data;
      const xs=exps.map(e=>day(e.expiry));
      // One value per ladder row per expiry, already in scale space. A strike
      // the column does not list is interpolated in log price between the
      // listed strikes either side, so a log field is interpolated
      // logarithmically as well.
      const REL_FIELD=colourBy!=='p';
      const P=exps.map(e=>{
        // Only strikes that carry a value for this field anchor the
        // interpolation. A contract whose own quote failed the checks has a
        // borrowed volatility but no open interest or spread; it is spanned
        // over rather than treated as a break.
        const ks=e.cells.map(c=>c.k).sort((a,b)=>a-b)
          .filter(k=>{const raw=val(cellAt(e,k));
                      if(raw==null)return false;
                      const t=scaleOf(raw); return t!=null&&isFinite(t);});
        const lk=ks.map(Math.log), vs=ks.map(k=>scaleOf(val(cellAt(e,k))));
        return rows.map(k=>{
          const c=cellAt(e,k);
          if(c){const raw=val(c);
                if(raw!=null){const t=scaleOf(raw);
                              if(t!=null&&isFinite(t))return t;}}
          if(ks.length<2)return null;
          const x=Math.log(k);
          // Outside the strikes a column lists, the field is left empty rather
          // than clamped to the edge value.
          if(x<lk[0]||x>lk[lk.length-1])return null;
          let i=0; while(i<lk.length-2&&lk[i+1]<x)i++;
          const t=(x-lk[i])/(lk[i+1]-lk[i]);
          return vs[i]+(vs[i+1]-vs[i])*t;
        });
      });

      if(!_lut)buildLut();
      // Probability has an absolute scale, zero to one, and is drawn on the
      // ramp directly. Every other field is relative and is stretched across
      // what the visible columns hold.
      const REL=colourBy!=='p';
      const INV=COLOUR[colourBy].invert===true;
      let VLO=0,VHI=1;
      if(REL){
        const all=[];
        exps.forEach(e=>e.cells.forEach(c=>{const v=val(c);
          if(v!=null){const t=scaleOf(v); if(t!=null&&isFinite(t))all.push(t);}}));
        all.sort((a,b)=>a-b);
        // The high end is the largest value, unclipped: the extremes are what
        // these maps are read for. The low end starts at the tenth percentile,
        // so a few one-lot contracts do not take up half of the log scale.
        const CLIP=COLOUR[colourBy].clip!==false;
        const LOQ=CLIP?0.05:0.10;
        VLO=all.length?all[Math.floor(all.length*LOQ)]:0;
        VHI=all.length?(CLIP?all[Math.floor(all.length*0.95)]
                             :all[all.length-1]):1;
        if(VHI<=VLO)VHI=VLO+1e-9;
      }
      // The dots are drawn in a later pass and must use the same scale.
      window._vlo=REL?VLO:null; window._vhi=REL?VHI:null;
      legendCaps(VLO,VHI);

      // The open-interest, spread and IV maps are painted outward from the
      // contracts rather than interpolated across a grid, which would need a
      // value at all four corners of every cell and leave whole bands blank
      // next to a sparse expiry.
      //
      // Each contract colours its own neighbourhood. A contract needs no
      // neighbours to be drawn; where several sit together their patches merge
      // into one block, and an isolated contract stays an island.
      //
      // Distance is measured in cells: one typical strike gap in log price
      // counts the same as one expiry gap in time, which keeps patches round
      // on screen. Beyond REACH of those units a pixel is left unpainted.
      const REACH=1.35, PW=2.6;
      // Evaluated on a coarse lattice and sampled bilinearly per pixel, which
      // looks the same and costs a few thousand sums per frame instead of
      // hundreds of thousands.
      const LW=120, LH=90;
      let LAT=null;
      // The lattice depends only on the symbol, the field and the range of
      // strikes and dates on screen. Scrolling changes none of these, so it is
      // kept and rebuilt only when one of them moves.
      const _key=REL?[cur,colourBy,kLo.toFixed(4),kHi.toFixed(4),
                      dNow,xs[xs.length-1],exps.length].join('|'):null;
      if(REL&&window._latKey===_key&&window._lat){
        LAT=window._lat;
      } else if(REL){
        // The strike unit is the typical gap between neighbouring listed
        // strikes, not the ladder's row spacing, so the patch size does not
        // depend on how many rows the export has.
        const _lks=[];
        exps.forEach(e=>e.cells.forEach(c=>{if(!c.synthetic)_lks.push(Math.log(c.k));}));
        _lks.sort((a,b)=>a-b);
        let _gap=0,_n=0;
        for(let q=1;q<_lks.length;q++){const g=_lks[q]-_lks[q-1];
          if(g>1e-9){_gap+=g;_n++;}}
        const dk=Math.max(1e-6,_n?(_gap/_n)*4:0.01);
        const dt=Math.max(1,(xs[xs.length-1]-xs[0])/Math.max(1,xs.length-1));
        const pts=[];
        exps.forEach((e,ci)=>{
          const ex=xs[ci];
          e.cells.forEach(c=>{
            if(c.synthetic)return;  // no contract, no source
            const raw=val(c);
            if(raw==null)return;
            const t=scaleOf(raw);
            if(t==null||!isFinite(t))return;
            pts.push({x:ex,lk:Math.log(c.k),v:t});
          });
        });
        const vg=new Float64Array(LW*LH), ag=new Uint8Array(LW*LH);
        const d0=dNow, d1=xs[xs.length-1];
        const lkLo=Math.log(kLo), lkHi=Math.log(kHi);
        const R2=REACH*REACH, FAR=R2*9, FARR=Math.sqrt(FAR);
        // Splatting: each contract writes into the lattice nodes within its
        // reach, instead of every node visiting every contract.
        const num=new Float64Array(LW*LH), den=new Float64Array(LW*LH);
        const nr2=new Float64Array(LW*LH).fill(Infinity);
        const sx=(LW-1)/Math.max(1e-9,d1-d0), sy=(LH-1)/Math.max(1e-9,lkHi-lkLo);
        for(let q=0;q<pts.length;q++){
          const s0=pts[q];
          const cx=(s0.x-d0)*sx, cy=(lkHi-s0.lk)*sy;
          // how many nodes FARR cell-units spans on each axis
          const rx=Math.ceil(FARR*dt*sx), ry=Math.ceil(FARR*dk*sy);
          const i1=Math.max(0,Math.floor(cx-rx)), i2=Math.min(LW-1,Math.ceil(cx+rx));
          const j1=Math.max(0,Math.floor(cy-ry)), j2=Math.min(LH-1,Math.ceil(cy+ry));
          for(let j=j1;j<=j2;j++){
            const lkp=lkHi-(j/(LH-1))*(lkHi-lkLo);
            const b0=(lkp-s0.lk)/dk, bb=b0*b0;
            for(let i=i1;i<=i2;i++){
              const dd2=d0+(i/(LW-1))*(d1-d0);
              const a=(dd2-s0.x)/dt;
              const r2=a*a+bb;
              const idx=j*LW+i;
              if(r2<nr2[idx])nr2[idx]=r2;
              if(r2>FAR)continue;
              // A contract's claim is strongest at its own strike and falls
              // with distance. Each node keeps the strongest claim rather than
              // the average, so a large position stays distinct from its
              // neighbours and a strike holding nothing stays pale next to it.
              const fall=1/(1+Math.pow(Math.sqrt(r2)/REACH,PW));
              const claim=s0.v*fall+VLO*(1-fall);
              if(den[idx]===0||claim>num[idx]){num[idx]=claim;den[idx]=1;}
            }
          }
        }
        for(let idx=0;idx<LW*LH;idx++){
          if(den[idx]>0&&nr2[idx]<=R2){vg[idx]=num[idx];ag[idx]=1;}
        }
        LAT={v:vg,a:ag,d0:d0,d1:d1,lkLo:lkLo,lkHi:lkHi,reachLog:REACH*dk};
        window._lat=LAT; window._latKey=_key;
      }
      // The contract envelope of each expiry, in log strike: the lowest and
      // highest listed contract, with half a strike gap of margin so an edge
      // contract keeps its own colour around it. Between expiries it is
      // interpolated in time.
      let ENV=null;
      if(REL){
        ENV=exps.map(e=>{
          const ks=e.cells.filter(c=>!c.synthetic).map(c=>Math.log(c.k))
                          .sort((a,b)=>a-b);
          if(!ks.length)return null;
          const n=ks.length;
          const gLo=n>1?ks[1]-ks[0]:0.01, gHi=n>1?ks[n-1]-ks[n-2]:0.01;
          // Beyond the outermost contract the colour fades out over the splat
          // reach, ending just inside it where the lattice runs out of values,
          // so the edge is never a hard line. Only transparency changes here;
          // colours inside the envelope are unaffected.
          const w=0.9*((LAT&&LAT.reachLog)||0.05);
          return {lo:ks[0], hi:ks[n-1], wLo:w, wHi:w};
        });
      }
      // Everything that depends only on a pixel's column (the bracketing
      // expiries, the envelope at that date, the lattice position) is computed
      // once per column, and likewise per row.
      const nX=wpx, spanD=xs[xs.length-1]-dNow;
      const cDD=new Float64Array(nX), cCI=new Int32Array(nX),
            cCF=new Float64Array(nX), cPre=new Uint8Array(nX);
      {
        let ci=0;
        for(let ix=0;ix<nX;ix++){
          const dd=dNow+((ix+ixOff)/(wFull-1))*spanD;
          while(ci<xs.length-2&&xs[ci+1]<dd)ci++;  // dd only grows with ix
          cDD[ix]=dd; cCI[ix]=ci;
          if(dd<=xs[0]){cPre[ix]=1; cCF[ix]=(dd-dNow)/Math.max(1,xs[0]-dNow);}
          else cCF[ix]=(dd-xs[ci])/(xs[ci+1]-xs[ci]);
        }
      }
      let cSkip,cELo,cEHi,cWLo,cWHi,cI0,cTX;
      if(LAT){
        cSkip=new Uint8Array(nX); cELo=new Float64Array(nX); cEHi=new Float64Array(nX);
        cWLo=new Float64Array(nX); cWHi=new Float64Array(nX);
        cI0=new Int32Array(nX); cTX=new Float64Array(nX);
        for(let ix=0;ix<nX;ix++){
          const dd=cDD[ix], ci=cCI[ix], A=ENV[ci], Bv=ENV[ci+1];
          // Beyond the contract envelope at this date the colour fades out
          // (see where ENV is built).
          if(dd<=xs[0]||!Bv){ const E=dd<=xs[0]?ENV[0]:A;
            if(!E){cSkip[ix]=1;continue;}
            cELo[ix]=E.lo; cEHi[ix]=E.hi; cWLo[ix]=E.wLo; cWHi[ix]=E.wHi; }
          else if(!A){ cELo[ix]=Bv.lo; cEHi[ix]=Bv.hi; cWLo[ix]=Bv.wLo; cWHi[ix]=Bv.wHi; }
          else {
            const f=(dd-xs[ci])/Math.max(1e-9,xs[ci+1]-xs[ci]);
            cELo[ix]=A.lo+(Bv.lo-A.lo)*f; cEHi[ix]=A.hi+(Bv.hi-A.hi)*f;
            cWLo[ix]=A.wLo+(Bv.wLo-A.wLo)*f; cWHi[ix]=A.wHi+(Bv.wHi-A.wHi)*f;
          }
          // Where the column falls on the lattice; off it, nothing is drawn.
          const fx=(dd-LAT.d0)/Math.max(1e-9,LAT.d1-LAT.d0)*(LW-1);
          if(fx<0||fx>LW-1){cSkip[ix]=1;continue;}
          const i0=Math.min(LW-2,Math.floor(fx)); cI0[ix]=i0; cTX[ix]=fx-i0;
        }
      }
      for(let iy=0;iy<hpx;iy++){
        const price=kHi-((iy+iyOff)/(hFull-1))*(kHi-kLo);
        // locate the strike bracket once per row
        let ri=0; while(ri<rows.length-2&&rows[ri+1]<price)ri++;
        const rf=(price-rows[ri])/(rows[ri+1]-rows[ri]);
        const rowO=iy*wpx*4;
        if(LAT){
          // Sample the lattice. A pixel whose four surrounding nodes are all
          // out of reach of every contract stays unpainted.
          const lp=Math.log(price);
          const fy=(LAT.lkHi-lp)/Math.max(1e-9,LAT.lkHi-LAT.lkLo)*(LH-1);
          if(fy<0||fy>LH-1)continue;
          const j0=Math.min(LH-2,Math.floor(fy)), ty=fy-j0, jb=j0*LW;
          const LA=LAT.a, LV=LAT.v;
          for(let ix=0;ix<nX;ix++){
            if(cSkip[ix])continue;
            const eLo=cELo[ix], eHi=cEHi[ix];
            const out=lp<eLo?(eLo-lp)/Math.max(1e-9,cWLo[ix])
                     :lp>eHi?(lp-eHi)/Math.max(1e-9,cWHi[ix]):0;
            if(out>=1)continue;
            const envA=1-out*out*(3-2*out);  // smoothstep: soft start, soft end
            const q00=jb+cI0[ix], q10=q00+1, q01=q00+LW, q11=q01+1;
            if(!LA[q00]||!LA[q10]||!LA[q01]||!LA[q11])continue;
            const tx=cTX[ix];
            const top=LV[q00]+(LV[q10]-LV[q00])*tx;
            const bot=LV[q01]+(LV[q11]-LV[q01])*tx;
            const p=top+(bot-top)*ty;
            const o2=rowO+ix*4;
            let u2=(p-VLO)/(VHI-VLO||1);
            if(INV)u2=1-u2;
            const k2=lutIdx(Math.min(1,Math.max(0,u2)))*3;
            px[o2]=_lut[k2];px[o2+1]=_lut[k2+1];px[o2+2]=_lut[k2+2];
            px[o2+3]=Math.round(226*envA);
          }
          continue;
        }
        const P0=P[0];
        for(let ix=0;ix<nX;ix++){
          const cf=cCF[ix];
          let p;
          if(cPre[ix]){  // between today and the first expiry
            const u0=P0[ri],u1=P0[ri+1];
            if(u0==null||u1==null)continue;
            const v0=u0+(u1-u0)*rf;
            // Probability is zero today and grows towards the first expiry, so
            // it ramps. Open interest, spread and volatility belong to the
            // contract, not to elapsed time, so they hold their value back to
            // today.
            p=REL?v0:v0*cf;
          } else {
            const ci=cCI[ix], Pa=P[ci], Pb=P[ci+1];
            const a0=Pa[ri],a1=Pa[ri+1],b0=Pb[ri],b1=Pb[ri+1];
            if(a0==null||a1==null||b0==null||b1==null)continue;  // nothing quoted here
            const a=a0+(a1-a0)*rf, b=b0+(b1-b0)*rf;
            p=a+(b-a)*cf;
          }
          const o=rowO+ix*4;
          // Normalise into 0..1, inverting where the low end is the favourable
          // one, then read the blue ramp. Relative fields keep a flat alpha.
          let u;
          if(REL){
            u=(p-VLO)/(VHI-VLO||1);
            if(INV)u=1-u;
            u=Math.min(1,Math.max(0,u));
          } else u=p;
          const k=lutIdx(u)*3;
          px[o]=_lut[k];px[o+1]=_lut[k+1];px[o+2]=_lut[k+2];
          px[o+3]=REL?226:alphaAt(p);
        }
      }
      octx.putImageData(img,0,0);
      ctx.drawImage(off,Math.round(gx0)+ixOff,Math.round(gy0)+iyOff);
    }
  }

  // One dot per listed option, in ink so they read against the field.
  window._bars={list:bars, x0:PADL+2*CW, cw:CW, top:TOP, h:PLOTH, y:y};
  window._inv={x2day:px=>slotDay((px-PADL)/CW-2), day2x:dd=>x(dd),
               y2price:py=>lo+(TOP+PLOTH-py)/PLOTH*(hi-lo), price2y:v=>y(v)};
  window._cells=[];
  const rDot=Math.max(1.6,Math.min(4,CW*0.42));
  exps.forEach(e=>{
    const cx=x(day(e.expiry));
    e.cells.forEach(c=>{
      // A synthetic cell has no contract: no dot, and nothing for the pointer
      // to find.
      if(c.synthetic)return;
      const cy=y(c.k);
      if(cy<TOP-20||cy>TOP+PLOTH+20)return;
      // Hiding the dots hides only the drawing. Every contract is still
      // registered for the pointer, so the tooltip and crosshair keep working
      // over a bare field.
      if(showDots){
        // A contract whose own quote failed the checks is drawn hollow: its
        // volatility is borrowed from a neighbour, not solved from its own
        // price.
        ctx.beginPath();ctx.arc(cx,cy,rDot,0,Math.PI*2);
        if(c.exact===false){
          ctx.fillStyle=css('--bg');ctx.fill();
          ctx.lineWidth=1.1;ctx.strokeStyle=css('--ink');ctx.stroke();
        } else {
          ctx.fillStyle=css('--ink');ctx.fill();
        }
      }
      window._cells.push({cx:cx,cy:cy,r:Math.max(rDot,8),e:e,c:c});
    });
  });

  // One probability, three models. Each model gets its own colour and the same
  // rule: mark the listed strike nearest the chosen figure at every expiry, on
  // each side of spot, and join them.
  if(trackOn){
    // Drawn in reverse so the implied contour, first in the list, is painted
    // last and stays on top.
    MODELS.slice().reverse().forEach(M=>{
      if(!modelOn[M.key])return;
      const field=fieldOf(M.key,contourKind);
      const col=css(M.col);
      [[false,trackDn],[true,trackUp]].forEach(([up,target])=>{
        if(contourKind==='pexp'){
          let ceil=0;
          d.expiries.forEach(e=>e.cells.forEach(c=>{
            if(c.up!==up)return;
            const v=c[field]; if(v!=null&&v>ceil)ceil=v;}));
          if(target>ceil-0.005)return;  // no strike can reach it
        }
        const tk=trackedStrikes(d,target,field,up);
        if(tk.length>=2){
          ctx.strokeStyle=col;ctx.lineWidth=1.5;ctx.setLineDash([4,3]);
          ctx.beginPath();
          tk.forEach((t,i)=>{const px=x(day(t.e.expiry)),py=y(t.c.k);
            i?ctx.lineTo(px,py):ctx.moveTo(px,py);});
          ctx.stroke();ctx.setLineDash([]);
        }
        tk.forEach(t=>{
          const px=x(day(t.e.expiry)), py=y(t.c.k);
          if(py<TOP-20||py>TOP+PLOTH+20)return;
          ctx.beginPath();ctx.arc(px,py,5,0,Math.PI*2);
          if(t.near){ctx.fillStyle=col;ctx.fill();
            ctx.strokeStyle=panel;ctx.lineWidth=1.5;ctx.stroke();}
          else{ctx.fillStyle=panel;ctx.fill();
            ctx.strokeStyle=col;ctx.lineWidth=1.5;ctx.stroke();}
        });
      });
    });
  }

  // The bar under the pointer, with a rule down the chart and its own figures.
  if(window._bx!=null&&window._bx>=0&&window._bx<bars.length){
    const b=bars[window._bx], bx=Math.round(x(day(b.t)))+.5;
    ctx.strokeStyle=ink3;ctx.lineWidth=1;ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(bx,TOP);ctx.lineTo(bx,TOP+PLOTH);ctx.stroke();
    ctx.setLineDash([]);
    const lines=[b.t,
      'O '+b.o.toFixed(2)+'   H '+b.h.toFixed(2),
      'L '+b.l.toFixed(2)+'   C '+b.c.toFixed(2)];
    ctx.font='500 10.5px "IBM Plex Mono",monospace';ctx.textBaseline='middle';
    const w=Math.max(...lines.map(t=>ctx.measureText(t).width))+14;
    const gut=(document.getElementById('scroller')||{}).scrollLeft||0;
    let lx=bx+8; if(lx+w>gut+(document.getElementById('scroller')||{clientWidth:900}).clientWidth) lx=bx-8-w;
    // Placed just above the candles below it, or just below them if there is
    // no room above, so it stays near the price without hiding bars.
    const bh2=lines.length*14+8;
    let hiP=-Infinity, loP=Infinity;
    for(let k=0;k<bars.length;k++){const q=bars[k], qx=x(day(q.t));
      if(qx>=lx-2&&qx<=lx+w+2){if(q.h>hiP)hiP=q.h;if(q.l<loP)loP=q.l;}}
    if(!isFinite(hiP)){hiP=b.h;loP=b.l;}
    let ly=y(hiP)-bh2-10;
    if(ly<TOP+4){ly=y(loP)+10; if(ly+bh2>TOP+PLOTH-4)ly=TOP+8;}
    ctx.fillStyle=panel;ctx.globalAlpha=.94;
    ctx.fillRect(lx,ly,w,lines.length*14+8);ctx.globalAlpha=1;
    ctx.strokeStyle=line2;ctx.lineWidth=1;
    ctx.strokeRect(lx+.5,ly+.5,w-1,lines.length*14+7);
    ctx.textAlign='left';
    lines.forEach((t,i)=>{
      ctx.fillStyle=i===0?css('--ink'):ink2;
      ctx.fillText(t,lx+7,ly+12+i*14);});
  }

  // Earnings dates on the date axis: a filled star where the date is
  // confirmed, hollow where it is projected from the reporting cadence,
  // smaller for past reports. An expiry that spans a results day prices a
  // different kind of risk, which often explains a jump in the implied
  // volatility term structure.
  window._earn=[];
  if(d.earnings){
    const ec=css('--earn');
    // An outlined star looks larger than a filled one of the same radius, so
    // the filled star is grown by half a stroke to match.
    const star=(cx,cy,r0,filled)=>{
      const r=filled?r0+0.65:r0;
      ctx.beginPath();
      for(let i=0;i<10;i++){
        const ang=-Math.PI/2+i*Math.PI/5, rr=i%2?r*0.45:r;
        const px=cx+Math.cos(ang)*rr, py=cy+Math.sin(ang)*rr;
        i?ctx.lineTo(px,py):ctx.moveTo(px,py);
      }
      ctx.closePath();
      if(filled){ctx.fillStyle=ec;ctx.fill();}
      else {ctx.fillStyle=panel;ctx.fill();
        ctx.strokeStyle=ec;ctx.lineWidth=1.3;ctx.stroke();}
    };
    d.earnings.forEach(e=>{
      const dd=day(e.d), cx=x(dd);
      if(cx<PADL-10||cx>W-PADR+10)return;
      const cy=TOP+PLOTH-7;
      if(!e.past){  // a faint rule so the date reads against the field
        ctx.strokeStyle=ec;ctx.globalAlpha=.30;ctx.lineWidth=1;
        ctx.setLineDash([2,4]);
        ctx.beginPath();ctx.moveTo(Math.round(cx)+.5,TOP);
        ctx.lineTo(Math.round(cx)+.5,cy-8);ctx.stroke();
        ctx.setLineDash([]);ctx.globalAlpha=1;
      }
      star(cx,cy,e.past?5:6,!!e.confirmed);
      window._earn.push({cx:cx,cy:cy,r:9,e:e});
    });
  }

  if(hover){  // re-find the hovered point in the new geometry and ring it
    const hx=x(day(hover.e.expiry)), hy=y(hover.c.k);
    ctx.beginPath();ctx.arc(hx,hy,Math.max(hover.r,9)+3,0,Math.PI*2);
    ctx.strokeStyle=css('--ink');ctx.lineWidth=1.5;ctx.stroke();
    ctx.strokeStyle=css('--line-2');ctx.lineWidth=1;ctx.setLineDash([3,3]);
    ctx.beginPath();ctx.moveTo(PADL,Math.round(hy)+.5);ctx.lineTo(hx,Math.round(hy)+.5);ctx.stroke();
    ctx.beginPath();ctx.moveTo(Math.round(hx)+.5,hy);ctx.lineTo(Math.round(hx)+.5,TOP+PLOTH);ctx.stroke();
    ctx.setLineDash([]);
  }

  // Model-free implied volatility per expiry (the VIX construction applied to
  // one expiry at its own maturity), in a badge above the highest listed
  // contract; the date and days go below the lowest. Because the cone widens
  // with time, neighbouring badges mostly fall at different heights; any that
  // still collide are pushed further out, and when columns are packed tight
  // the badges shrink to the volatility alone.
  window._ivb=[];
  const _placed=(window._earn||[]).map(o=>({x:o.cx-8,y:o.cy-8,w:16,h:16}));
  const _hit=a=>_placed.some(b=>a.x<b.x+b.w+2&&a.x+a.w+2>b.x&&a.y<b.y+b.h+2&&a.y+a.h+2>b.y);
  const _edge=(e,top)=>{let v=top?-Infinity:Infinity;
    e.cells.forEach(c=>{if(c.synthetic)return; v=top?Math.max(v,c.k):Math.min(v,c.k);});
    return isFinite(v)?v:null;};
  let _gap=Infinity;
  for(let i=1;i<exps.length;i++)_gap=Math.min(_gap,x(day(exps[i].expiry))-x(day(exps[i-1].expiry)));
  const compact=_gap<56;
  exps.forEach(e=>{
    if(e.mf_iv==null)return;
    const cx=x(day(e.expiry)), bw=compact?46:52, bh=compact?20:40;
    const kt=_edge(e,true), ty=kt==null?TOP:y(kt);
    const r={x:cx-bw/2,y:Math.max(PADT-4,Math.min(ty-10-bh,TOP+PLOTH-bh-4)),w:bw,h:bh};
    for(let g=0;g<80&&_hit(r)&&r.y>PADT-4;g++)r.y-=4;
    _placed.push(r);
    const bx=r.x, by=r.y;
    ctx.strokeStyle=line2;ctx.setLineDash([2,3]);ctx.lineWidth=1;
    if(ty>by+bh+2){ctx.beginPath();ctx.moveTo(Math.round(cx)+.5,by+bh);
      ctx.lineTo(Math.round(cx)+.5,Math.min(ty-4,TOP+PLOTH));ctx.stroke();}
    ctx.setLineDash([]);
    ctx.fillStyle=panel;ctx.strokeStyle=line2;ctx.lineWidth=1;
    ctx.beginPath();ctx.roundRect?ctx.roundRect(bx,by,bw,bh,3):ctx.rect(bx,by,bw,bh);
    ctx.fill();ctx.stroke();
    // a hairline in the field's own colour ties the badge to its column
    ctx.fillStyle=probColor(Math.min(1,e.mf_iv*2.2));
    ctx.fillRect(bx,by,bw,2.5);
    ctx.textAlign='center';ctx.textBaseline='middle';
    ctx.fillStyle=css('--ink');ctx.font=(compact?'600 11px':'600 12px')+' "IBM Plex Mono",monospace';
    ctx.fillText((e.mf_iv*100).toFixed(1)+'%',cx,by+(compact?11:15));
    if(!compact&&e.ivrv!=null){
      // the implied-to-realized ratio, coloured by how far above realized
      // volatility the market is pricing
      const rr=e.ivrv;
      ctx.fillStyle = rr>=1.30?css('--track') : rr>=1.05?css('--ink-2') : css('--ink-3');
      ctx.font='600 10.5px "IBM Plex Mono",monospace';
      ctx.fillText('x'+rr.toFixed(2),cx,by+30);
    }
    window._ivb.push({x:bx,y:by,w:bw,h:bh,e:e});
  });
  exps.forEach(e=>{
    const cx=x(day(e.expiry)), bw=compact?34:46, bh=compact?16:28;
    const kb=_edge(e,false), ly=kb==null?TOP+PLOTH:y(kb);
    const r={x:cx-bw/2,y:Math.min(TOP+PLOTH-bh-2,Math.max(TOP,ly+10)),w:bw,h:bh};
    for(let g=0;g<80&&_hit(r)&&r.y<TOP+PLOTH-bh-2;g++)r.y+=4;
    _placed.push(r);
    ctx.strokeStyle=line2;ctx.setLineDash([2,3]);ctx.lineWidth=1;
    if(r.y>ly+6){ctx.beginPath();ctx.moveTo(Math.round(cx)+.5,Math.max(ly+4,TOP));
      ctx.lineTo(Math.round(cx)+.5,r.y);ctx.stroke();}
    ctx.setLineDash([]);
    ctx.fillStyle=panel;ctx.strokeStyle=line2;ctx.lineWidth=1;
    ctx.beginPath();ctx.roundRect?ctx.roundRect(r.x,r.y,bw,bh,3):ctx.rect(r.x,r.y,bw,bh);
    ctx.fill();ctx.stroke();
    ctx.textAlign='center';ctx.textBaseline='middle';
    if(compact){
      ctx.fillStyle=ink2;ctx.font='600 10px "IBM Plex Mono",monospace';
      ctx.fillText(e.dte+'d',cx,r.y+bh/2+.5);
    } else {
      ctx.fillStyle=ink2;ctx.font='600 10px "IBM Plex Mono",monospace';
      ctx.fillText(e.expiry.slice(5),cx,r.y+9.5);
      ctx.fillStyle=ink3;ctx.font='10px "IBM Plex Mono",monospace';
      ctx.fillText(e.dte+'d',cx,r.y+20.5);
    }
  });
  // The price axis is painted last, over a panel-coloured band at the current
  // scroll offset, so it stays legible however far the view has moved.
  const sx=(document.getElementById('scroller')||{}).scrollLeft||0;
  ctx.fillStyle=panel;ctx.fillRect(sx,0,PADL,H);
  ctx.strokeStyle=line;ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(Math.round(sx+PADL)+.5,0);
  ctx.lineTo(Math.round(sx+PADL)+.5,TOP+PLOTH);ctx.stroke();
  ctx.font='11px "IBM Plex Mono",monospace';
  ctx.textAlign='right';ctx.textBaseline='middle';
  ticks.forEach(([v,yy])=>{
    ctx.strokeStyle=line;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(sx+PADL-4,yy);ctx.lineTo(sx+PADL,yy);ctx.stroke();
    ctx.fillStyle=ink3;
    ctx.fillText(major<1?v.toFixed(2):v.toFixed(0),sx+PADL-8,yy);
  });
  {const ly=Math.round(y(d.spot))+.5, t=d.spot.toFixed(2);
   ctx.font='600 10.5px "IBM Plex Mono",monospace';
   const tw=ctx.measureText(t).width;
   ctx.fillStyle=css('--spot');ctx.fillRect(sx+PADL-tw-12,ly-8,tw+10,16);
   ctx.fillStyle=panel;ctx.textAlign='right';ctx.fillText(t,sx+PADL-6,ly);}
  ctx.fillStyle=ink3;ctx.font='9.5px "IBM Plex Mono",monospace';ctx.textAlign='right';
  ctx.fillText('IV %',sx+PADL-8,PADT+11);
  ctx.fillText('IV/RV',sx+PADL-8,PADT+26);

  // User drawings, in a colour used by neither the field nor the contours.
  {
    const dc=css('--draw');
    const paint=(o,live)=>{
      ctx.strokeStyle=dc;ctx.lineWidth=live?1.2:1.5;
      ctx.globalAlpha=o.ghost?0.75:1;
      ctx.setLineDash(live&&!o.ghost?[4,4]:o.ghost?[6,4]:[]);
      ctx.beginPath();
      const gut=(document.getElementById('scroller')||{}).scrollLeft||0;
      if(o.kind==='h'){
        const py=Math.round(y(o.p))+.5;
        ctx.moveTo(gut+PADL,py);ctx.lineTo(W-PADR,py);
      } else {
        ctx.moveTo(x(o.d),y(o.p));ctx.lineTo(x(o.d2),y(o.p2));
      }
      ctx.stroke();ctx.setLineDash([]);ctx.globalAlpha=1;
      if(o.kind==='h'){  // the level it marks
        const py=Math.round(y(o.p))+.5, lab=o.p.toFixed(2);
        ctx.font='600 10px "IBM Plex Mono",monospace';ctx.textAlign='left';
        ctx.textBaseline='middle';
        const lw=ctx.measureText(lab).width;
        ctx.fillStyle=panel;ctx.fillRect(gut+PADL+6,py-8,lw+8,16);
        ctx.strokeStyle=dc;ctx.lineWidth=1;ctx.strokeRect(gut+PADL+6.5,py-7.5,lw+7,15);
        ctx.fillStyle=dc;ctx.fillText(lab,gut+PADL+10,py);
      }
      if(o.kind==='t'&&!live){  // endpoint handles
        [[o.d,o.p],[o.d2,o.p2]].forEach(([dd,pp])=>{
          ctx.beginPath();ctx.arc(x(dd),y(pp),3.5,0,Math.PI*2);
          ctx.fillStyle=dc;ctx.fill();
          ctx.strokeStyle=panel;ctx.lineWidth=1;ctx.stroke();});
      }
    };
    drawings.forEach(o=>paint(o,false));
    if(pending)paint(pending,true);
    if(ghost)paint(ghost,true);
  }


  // x axis: the date granularity follows the zoom.
  ctx.fillStyle=ink3;ctx.font='10px "IBM Plex Mono",monospace';ctx.textAlign='center';
  const dayPx=CW;
  let mode = dayPx>=26 ? 'day' : dayPx>=9 ? 'week' : dayPx>=3 ? 'month' : 'quarter';
  let lastKey='';
  bars.forEach((b,i)=>{
    const dt=new Date(b.t+'T00:00:00Z'), m=b.t.slice(0,7);
    let hit=false, label='';
    if(mode==='day'){hit=true;label=b.t.slice(8,10);
      if(m!==lastKey){lastKey=m;label=b.t.slice(5,10);}}
    else if(mode==='week'){hit=dt.getUTCDay()===1;label=b.t.slice(5,10);}
    else if(mode==='month'){hit=m!==lastKey;if(hit)lastKey=m;label=b.t.slice(2,7);}
    else {const q=m.slice(0,4)+'Q'+Math.floor(+m.slice(5,7)/3.01);
      hit=q!==lastKey;if(hit)lastKey=q;label=b.t.slice(2,7);}
    if(!hit)return;
    const cx=x(day(b.t));
    ctx.strokeStyle=line;ctx.beginPath();
    ctx.moveTo(Math.round(cx)+.5,TOP+PLOTH);ctx.lineTo(Math.round(cx)+.5,TOP+PLOTH+4);ctx.stroke();
    ctx.fillText(label,cx,TOP+PLOTH+15);
  });
  exps.forEach(e=>{
    const cx=x(day(e.expiry));
    ctx.strokeStyle=line2;ctx.beginPath();ctx.moveTo(Math.round(cx)+.5,TOP+PLOTH);ctx.lineTo(Math.round(cx)+.5,TOP+PLOTH+4);ctx.stroke();
  });
}

// What the data table shows: the values the cone is coloured by, or each
// contract's delta, for comparing a whole chain with a broker's.
let tableMode='cone';
function table(){
  // The table shows whatever the cone is coloured by (touch probability,
  // implied volatility, open interest or spread) for tradable contracts only:
  // a row appears only where at least one expiry lists that strike.
  const d=DATA[cur], C=COLOUR[colourBy], DL=tableMode==='delta';
  const val=c=>{
    if(!c||c.synthetic)return null;
    const v=DL?c.delta:C.field(c); return (v==null||!isFinite(v))?null:v;};
  const fmt=v=>DL?v.toFixed(3):colourBy==='oi'?Math.round(v).toLocaleString('en-US'):(v*100).toFixed(1)+'%';
  const title=DL?'delta: calls above spot, puts below':
    ({p:'touch probability, implied',iv:'implied volatility',
      oi:'open interest',spr:'spread, % of mid'}[colourBy]||C.label);
  let h='<div class="scroller"><table><caption class="note" style="text-align:left;caption-side:top">'+
    title+'</caption><thead><tr><th>Strike</th><th>vs spot</th>'+
    d.expiries.map(e=>'<th>'+e.expiry.slice(5)+' &middot; '+e.dte+'d</th>').join('')+'</tr></thead><tbody>';
  d.rows.slice().reverse().forEach(k=>{
    const cs=d.expiries.map(e=>cellAt(e,k));
    const c0=cs.find(c=>c&&!c.synthetic);
    if(!c0)return;
    const atm=Math.abs(c0.pct)<2.0?' class="atm"':'';
    h+='<tr'+atm+'><td class="mono">'+k.toFixed(2)+'</td><td class="mono">'+(c0.pct>0?'+':'')+c0.pct.toFixed(1)+'%</td>'+
      cs.map(c=>{const v=val(c);
        return '<td class="mono">'+(v==null?'&middot;':fmt(v))+'</td>';}).join('')+'</tr>';
  });
  h+='</tbody><tfoot><tr><th>ATM IV</th><th></th>'+
    d.expiries.map(e=>'<th class="mono">'+(e.atm_iv*100).toFixed(1)+'%</th>').join('')+'</tr></tfoot></table></div>';
  document.getElementById('tbl').innerHTML=h;
}

const tip=document.getElementById('tip'), cvEl=document.getElementById('cv');
let hover=null;
const pct2=v=>v==null?'  n/a':(v*100).toFixed(1).padStart(5)+'%';
cvEl.addEventListener('mousemove',ev=>{
  // The session under the pointer; the axis counts sessions, so this is a
  // division.
  {
    const rb=document.getElementById('stage').getBoundingClientRect(), B=window._bars;
    if(B){
      const sx=(ev.clientX-rb.left-B.x0)/B.cw;
      const i=Math.round(sx);
      const my=ev.clientY-rb.top;
      const inPlot=my>=B.top&&my<=B.top+B.h;
      const want=(inPlot&&i>=0&&i<B.list.length)?i:null;
      if(want!==window._bx){window._bx=want;draw();}
    }
  }
  if(tool!=='none'){tip.style.opacity=0;return;}
  const r=document.getElementById('stage').getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;
  const er=(window._earn||[]).find(o=>
    (mx-o.cx)*(mx-o.cx)+(my-o.cy)*(my-o.cy)<=o.r*o.r);
  if(er){
    const e=er.e;
    tip.textContent='earnings  '+e.d+
      '\n'+(e.confirmed?'confirmed by the feed':'projected from the cadence')+
      (e.when?'\n'+(e.when==='bmo'?'before the open':'after the close'):'')+
      (e.past?'\nalready reported':'');
    tip.style.opacity=1;
    tip.style.left=Math.max(4,Math.min(er.cx+12,r.width-200))+'px';
    tip.style.top=Math.max(4,er.cy-74)+'px';
    if(hover){hover=null;draw();}
    return;
  }
  const b=(window._ivb||[]).find(o=>mx>=o.x&&mx<=o.x+o.w&&my>=o.y&&my<=o.y+o.h);
  if(b){
    const e=b.e;
    tip.textContent='model-free IV  '+(e.mf_iv*100).toFixed(2)+'%\n'+
      'at-the-money   '+(e.atm_iv*100).toFixed(2)+'%\n'+
      'expiry '+e.expiry+'  ('+e.dte+'d)\n'+
      e.mf_n+' strikes, K '+e.mf_lo+'-'+e.mf_hi+'\n'+
      'forward '+e.mf_f+
      (e.ivrv!=null?'\nIV / RV30     '+e.ivrv.toFixed(2)+'x':'');
    tip.style.opacity=1;
    tip.style.left=Math.max(4,Math.min(b.x+b.w+8,r.width-220))+'px';
    tip.style.top=(b.y+b.h+6)+'px';
    if(hover){hover=null;draw();}
    return;
  }
  let c=null,best=Infinity;
  (window._cells||[]).forEach(o=>{
    const d2=(mx-o.cx)*(mx-o.cx)+(my-o.cy)*(my-o.cy);
    if(d2<=o.r*o.r&&d2<best){best=d2;c=o;}
  });
  if(c){
    const f1=v=>v==null?'  n/a ':(v*100).toFixed(1).padStart(5)+'%';
    const num=(v,d)=>v==null?'n/a':v.toFixed(d==null?2:d);
    // The tooltip shows the field the cone is coloured by. For probability it
    // shows all three models, since their disagreement is the point.
    //
    // Delta and gamma are the contract's own, for comparing with a broker.
    // Delta is not the probability of finishing in the money: that is N(d2),
    // the implied expire figure, which differs from delta more as volatility
    // times root-time grows.
    const greek=(c.c.delta!=null
      ?'delta '+c.c.delta.toFixed(3)+(c.c.gamma!=null?'   gamma '+c.c.gamma.toFixed(4):'')+'\n':'');
    const head='strike '+c.c.k.toFixed(2)+'  ('+(c.c.pct>0?'+':'')+c.c.pct.toFixed(1)+'%)   '
      +c.e.expiry+'  '+c.e.dte+'d\n'+greek;
    const warn=(c.c.warn?'\n\u26a0 '+c.c.warn+' quote warning'+(c.c.warn>1?'s':''):'');
    let body;
    if(colourBy==='oi'){
      body='open interest  '+(c.c.oi==null?'n/a':c.c.oi.toLocaleString('en-US'))+'\n'
         +'volume today   '+(c.c.vol==null?'n/a':c.c.vol.toLocaleString('en-US'));
    } else if(colourBy==='iv'){
      body='implied vol    '+(c.c.iv==null?'n/a':(c.c.iv*100).toFixed(1)+'%')+'\n'
         +(c.c.up?'call':'put');
    } else if(colourBy==='spr'){
      body='bid / ask      '+num(c.c.bid)+' / '+num(c.c.ask)+'\n'
         +'spread         '+num(c.c.sprusd)+'   '
         +(c.c.spr==null?'n/a':(c.c.spr*100).toFixed(1)+'%')+'\n'
         +'mid            '+num(c.c.mid);
    } else {
      body='IV '+(c.c.iv==null?'n/a':(c.c.iv*100).toFixed(1)+'%')+'   '
         +(c.c.up?'from below':'from above')+'\n\n'
         +'           touch  expire\n'
         +'  implied '+f1(c.c.p)+' '+f1(c.c.pexp)+'\n'
         +'  5y      '+f1(c.c.mc5d)+' '+f1(c.c.mc5dexp)+'\n'
         +'  10y     '+f1(c.c.mc10d)+' '+f1(c.c.mc10dexp)
         +(c.c.mid!=null?'\n\nmid '+c.c.mid.toFixed(2):'');
    }
    tip.textContent=head+body+warn;
    tip.style.opacity=1;
    tip.style.left=Math.max(4,Math.min(c.cx+14,r.width-214))+'px';
    tip.style.top=Math.min(c.cy+14,r.height-92)+'px';
    if(hover!==c){hover=c;draw();}
  } else { tip.style.opacity=0; if(hover){hover=null;draw();} }
});
cvEl.addEventListener('mouseleave',()=>{tip.style.opacity=0;if(window._bx!=null){window._bx=null;draw();}if(hover){hover=null;draw();}});

// Ctrl + wheel zooms the calendar about the pointer. The pointer position is
// measured against the scroller, not the canvas, which already contains the
// scroll offset. The price axis refits itself afterwards, so only x is handled
// here.
//
// Wheel events arrive faster than a frame can be drawn, so the movement is
// collected and applied once per frame, in proportion to how far the wheel
// turned, with a single redraw.
let _zAcc=1, _zCursor=0, _zPending=false, _zSkipScroll=false;
function wheelZoom(ev){
  if(!ev.ctrlKey&&!ev.metaKey&&!ev.shiftKey)return;
  ev.preventDefault();
  const sc=document.getElementById('scroller');
  // Shift turns a vertical wheel into a horizontal one in most browsers, so
  // the movement may arrive on either axis. Lines and pages become pixels.
  const raw=ev.deltaY||ev.deltaX||0;
  const dy=raw*(ev.deltaMode===1?16:ev.deltaMode===2?400:1);
  _zAcc*=Math.exp(-dy*0.0014);  // one mouse notch is about 15%
  _zCursor=ev.clientX-sc.getBoundingClientRect().left;
  if(_zPending)return;
  _zPending=true;
  requestAnimationFrame(()=>{
    _zPending=false;
    const next=Math.min(ZOOM_MAX,Math.max(ZOOM_MIN,zoom*_zAcc));
    _zAcc=1;
    if(next===zoom)return;
    const cursor=_zCursor, before=sc.scrollLeft+cursor;
    // The day under the pointer at the current zoom, so it can be put back
    // under the pointer at the new one.
    const dayAt=(before-PADL)/(CW_FIT*zoom);
    zoom=next;
    yCenter=null;
    // Size the stage for the new zoom before moving the view, so the scroll
    // position can land where it should; then draw once.
    const G=window._geom, CW2=CW_FIT*zoom;
    if(G){document.getElementById('stage').style.width=
      (PADL+G.span*CW2+PADR+Math.max(0,60-6*CW2))+'px';}
    const target=Math.max(0,PADL+dayAt*CW2-cursor);
    if(Math.round(target)!==Math.round(sc.scrollLeft))_zSkipScroll=true;
    sc.scrollLeft=target;
    draw();zlabel();
  });
}
// Bound on the scroller rather than the canvas so the gesture works anywhere
// over the chart, including the margins.
document.getElementById('scroller')
  .addEventListener('wheel',wheelZoom,{passive:false});

function zlabel(){
  const el=document.getElementById('yz');
  if(el)el.textContent=Math.abs(zoom-ZOOM_HOME)<.01?'fit':zoom.toFixed(2)+'×';
}
document.getElementById('yreset').onclick=()=>{zoom=ZOOM_HOME;yCenter=null;yStretch=1;yShift=0;draw();zlabel();};

// The quality report. The headline rate counts contracts nobody reads, so the
// figure that matters is the one over the out-of-the-money contracts the
// probabilities are priced from.
function dqRender(){
  const d=DATA[cur], q=d.dq, el=document.getElementById('dqout');
  if(!el)return;
  if(!q){el.innerHTML='<i>no report for this pull</i>';return;}
  const pc=v=>(v*100).toFixed(0)+'%';
  let h='<div>'+q.n+' contracts, <b>'+q.n_used+'</b> out of the money and '+
    'therefore used. Captured with the market <b>'+q.state+'</b>'+
    (q.state!=='REGULAR'?' (quotes outside trading hours are placeholders)'
      :'')+'.</div>'+
    '<div style="margin-top:6px">Clean among the contracts used: '+
    '<span class="v'+q.verdict+'">'+pc(q.clean_used)+' &middot; '+q.verdict+
    '</span>  (all contracts '+pc(q.clean_all)+')</div>';
  h+='<div class="scroller"><table><thead><tr><th>moneyness</th><th>n</th>'+
     '<th>clean</th><th>spread</th><th>open int.</th><th>med mid</th></tr></thead><tbody>';
  (q.bands||[]).forEach(b=>{
    h+='<tr><td class="mono">'+b.lo.toFixed(2)+'&ndash;'+b.hi.toFixed(2)+'</td>'+
      '<td class="mono">'+b.n+'</td>'+
      '<td class="mono '+(b.clean>=0.85?'pos':b.clean<0.5?'neg':'')+'">'+pc(b.clean)+'</td>'+
      '<td class="mono">'+pc(b.median_spread)+'</td>'+
      '<td class="mono">'+Math.round(b.median_oi)+'</td>'+
      '<td class="mono">'+(b.median_mid!=null&&isFinite(b.median_mid)
        ?b.median_mid.toFixed(2):'&middot;')+'</td></tr>';
  });
  h+='</tbody></table></div>';
  h+='<p class="note">The money is where the volatility comes from and the wings are where the low probabilities live, so a single headline rate hides which half is failing. A quote passes when its spread is at most a quarter of the mid.</p>';
  el.innerHTML=h;
}

function readout(){
  if(!DATA[cur])return;  // app shell: data not loaded yet
  const d=DATA[cur], el=document.getElementById('trackout');
  document.getElementById('pvaldn').textContent=(trackDn*100).toFixed(0)+'%';
  document.getElementById('pvalup').textContent=(trackUp*100).toFixed(0)+'%';
  document.getElementById('plink').setAttribute('aria-pressed',String(linked));
  if(!trackOn){el.innerHTML='';return;}
  // Say when the expire contour cannot be drawn because no strike reaches the
  // target.
  const _ceil=up=>{let m=0;
    d.expiries.forEach(e=>e.cells.forEach(c=>{
      if(c.up!==up)return;
      const v=c[fieldOf('',contourKind)];
      if(v!=null&&v>m)m=v;}));
    return contourKind==='p'?1:m;};
  const cDn=_ceil(false), cUp=_ceil(true);
  const hid=(trackDn>cDn-0.005)||(trackUp>cUp-0.005);
  el.innerHTML=hid
    ? '<span class="rline" style="opacity:.7">expire contour hidden: no strike reaches '+
      (Math.max(trackDn,trackUp)*100).toFixed(0)+'% (ceiling '+
      (Math.min(cDn,cUp)*100).toFixed(0)+'% down, '+(cUp*100).toFixed(0)+'% up)</span>'
    : '';
}

function fieldLabel(){
  const d=DATA[cur];
  const pv=document.getElementById('prov');
  if(pv)pv.textContent=provText(d&&d.archive);
  const fl=document.getElementById('fieldlab');
  if(fl)fl.textContent=COLOUR[colourBy].label;
}

function setTrack(which,p){
  const v=Math.min(0.95,Math.max(0.05,Math.round(p*20)/20));
  if(linked){trackDn=v;trackUp=v;}
  else if(which==='dn')trackDn=v; else trackUp=v;
  draw();readout();
}
document.getElementById('pdn+').onclick=()=>setTrack('dn',trackDn+0.05);
document.getElementById('pdn-').onclick=()=>setTrack('dn',trackDn-0.05);
document.getElementById('pup+').onclick=()=>setTrack('up',trackUp+0.05);
document.getElementById('pup-').onclick=()=>setTrack('up',trackUp-0.05);
document.getElementById('plink').onclick=()=>{
  linked=!linked;
  if(linked)trackUp=trackDn;  // rejoin on the downside value
  draw();readout();};

[['ck-p','p'],['ck-pexp','pexp']].forEach(([id,v])=>{
  const b=document.getElementById(id);
  if(b)b.onclick=()=>{contourKind=v;
    [['ck-p','p'],['ck-pexp','pexp']].forEach(([j,w])=>{
      const e=document.getElementById(j);
      if(e)e.setAttribute('aria-pressed',String(w===v));});
    draw();readout();};
});

MODELS.forEach(M=>{
  const b=document.getElementById('md-'+M.key);
  if(b)b.onclick=()=>{modelOn[M.key]=!modelOn[M.key];
    b.setAttribute('aria-pressed',String(modelOn[M.key]));draw();};
});

(function(){const b=document.getElementById('dots');
  if(b)b.onclick=()=>{showDots=!showDots;
    b.setAttribute('aria-pressed',String(showDots));draw();};})();

[['cm-p','p'],['cm-iv','iv'],['cm-oi','oi'],['cm-spr','spr']].forEach(([id,v])=>{
  const b=document.getElementById(id);
  if(b)b.onclick=()=>{colourBy=v;
    [['cm-p','p'],['cm-iv','iv'],['cm-oi','oi'],['cm-spr','spr']].forEach(([j,w])=>{
      const e=document.getElementById(j);
      if(e)e.setAttribute('aria-pressed',String(w===v));});
    yCenter=null;draw();legend();fieldLabel();table();};
});

document.querySelectorAll('.stepper').forEach((el,i)=>{
  el.addEventListener('wheel',ev=>{ev.preventDefault();
    const which=i===0?'dn':'up';
    setTrack(which,(which==='dn'?trackDn:trackUp)+(ev.deltaY<0?0.05:-0.05));},
    {passive:false});
});
document.addEventListener('keydown',ev=>{
  if(ev.target.tagName==='INPUT')return;
  if(ev.key==='ArrowUp'){setTrack('dn',trackDn+0.05);ev.preventDefault();}
  if(ev.key==='ArrowDown'){setTrack('dn',trackDn-0.05);ev.preventDefault();}
  const k=ev.key.toLowerCase();
  if(k==='v')setTool('none');
  if(k==='t')setTool('tl');
  if(k==='h')setTool('hl');
  if((k==='z'&&(ev.metaKey||ev.ctrlKey))||k==='backspace'){
    if(drawings.length){drawings.pop();draw();ev.preventDefault();}}
});

// Panning. Dragging moves the chart; the scrollbar is hidden because the
// gesture replaces it. An active drawing tool takes precedence, since a drag
// then means a line.
(function(){
  const sc=document.getElementById('scroller');
  let down=false,x0=0,s0=0,moved=0,y0=0,ys0=0;
  sc.addEventListener('pointerdown',ev=>{
    if(tool!=='none')return;
    down=true;moved=0;x0=ev.clientX;s0=sc.scrollLeft;y0=ev.clientY;ys0=yShift;
    sc.classList.add('grabbing');
  });
  window.addEventListener('pointermove',ev=>{
    if(!down)return;
    const dx=ev.clientX-x0;moved=Math.max(moved,Math.abs(dx));
    sc.scrollLeft=s0-dx;
    yCenter=null;  // refit the price range to the new view
    // Dragging up or down slides the price window, so parts of the cone cut
    // off by the fit can be pulled into view. Reset returns it to centre.
    yShift=ys0+(ev.clientY-y0)/PLOTH;
    if(!window._sticky){window._sticky=true;
      requestAnimationFrame(()=>{window._sticky=false;draw();});}
  });
  window.addEventListener('pointerup',()=>{
    down=false;sc.classList.remove('grabbing');});
})();

// Drawing
function setTool(t){
  tool=t;pending=null;ghost=null;
  ['none','tl','hl'].forEach(k=>{
    const b=document.getElementById('tool-'+k);
    if(b)b.setAttribute('aria-pressed',String(k===t));});
  cvEl.classList.toggle('drawing',t!=='none');
  draw();
}
['none','tl','hl'].forEach(k=>{
  const b=document.getElementById('tool-'+k);
  if(b)b.onclick=()=>setTool(k);
});
document.getElementById('clear-draw').onclick=()=>{drawings=[];pending=null;ghost=null;draw();};

function atEvent(ev){
  const r=document.getElementById('stage').getBoundingClientRect(), inv=window._inv;
  if(!inv)return null;
  return {d:inv.x2day(ev.clientX-r.left), p:inv.y2price(ev.clientY-r.top)};
}
cvEl.addEventListener('pointerdown',ev=>{
  if(tool==='none')return;
  ev.preventDefault();
  const a=atEvent(ev); if(!a)return;
  if(tool==='hl'){ drawings.push({kind:'h',p:a.p}); ghost=null; draw(); return; }
  pending={kind:'t',d:a.d,p:a.p,d2:a.d,p2:a.p};
  cvEl.setPointerCapture(ev.pointerId);
});
cvEl.addEventListener('pointermove',ev=>{
  if(tool==='hl'){
    // Follow the pointer on every move so the level can be placed by eye
    // before it is committed.
    const a=atEvent(ev); if(!a)return;
    ghost={kind:'h',p:a.p,ghost:true};draw();return;
  }
  if(!pending)return;
  const a=atEvent(ev); if(!a)return;
  pending.d2=a.d;pending.p2=a.p;draw();
});
cvEl.addEventListener('pointerout',ev=>{
  if(ev.relatedTarget&&cvEl.contains(ev.relatedTarget))return;
  if(ghost){ghost=null;draw();}
});

const finish=ev=>{
  if(!pending)return;
  // A click without a drag is not a line; drop it.
  const inv=window._inv;
  if(inv&&Math.abs(inv.day2x(pending.d2)-inv.day2x(pending.d))+
          Math.abs(inv.price2y(pending.p2)-inv.price2y(pending.p))>6)
    drawings.push(pending);
  pending=null;draw();
};
cvEl.addEventListener('pointerup',finish);
cvEl.addEventListener('pointercancel',finish);

// Fullscreen moves the track bar into the panel so the controls stay with the
// chart, and gives the plot the remaining window height.
let fsOn=false, PLOTH_PAGE=PLOTH;
function setFull(on){
  fsOn=on;
  const panel=document.getElementById('panel'),
        bar=document.querySelector('.bar.track'),
        host=document.getElementById('fsbar'),
        home=document.getElementById('trackhome');
  panel.classList.toggle('fs',on);
  document.body.classList.toggle('fslock',on);
  if(on)host.appendChild(bar); else home.appendChild(bar);
  document.getElementById('fs').textContent=on?'exit':'fullscreen';
  document.getElementById('fs').setAttribute('aria-pressed',String(on));
  requestAnimationFrame(()=>{
    if(on){
      const used=host.offsetHeight+
        (document.getElementById('legendbar')||{offsetHeight:0}).offsetHeight;
      PLOTH=Math.max(320,window.innerHeight-used-IVH-AXISH-PADT-10);
    } else PLOTH=PLOTH_PAGE;
    draw();readout();
  });
}
document.getElementById('fs').onclick=()=>setFull(!fsOn);
document.addEventListener('keydown',ev=>{
  if(ev.target.tagName==='INPUT')return;
  if(ev.key==='Escape'&&fsOn)setFull(false);
  if((ev.key==='f'||ev.key==='F')&&!ev.metaKey&&!ev.ctrlKey)setFull(!fsOn);
});
window.addEventListener('resize',()=>{if(fsOn)setFull(true);});

document.getElementById('scroller').addEventListener('scroll',()=>{
  if(_zSkipScroll){_zSkipScroll=false;return;}  // a zoom step, already drawn
  if(!window._sticky){window._sticky=true;
    requestAnimationFrame(()=>{window._sticky=false;draw();});}
},{passive:true});

// Where the tickers come from. The all-in-one page has every ticker built in.
// The app page is an empty shell: it reads tickers/index.js for the list and
// loads tickers/SYM.js when a ticker is first shown. Each file carries its
// export time as a version, so a refreshed ticker is never served from a stale
// cache.
const OC_VER={};
window.OC_INDEX=function(idx){Object.assign(OC_VER,idx||{});};
window.OC_LOADED=function(s,obj){DATA[s]=obj;};
function ocList(){return OC_SHELL?Object.keys(OC_VER).sort():Object.keys(DATA);}
function ocNote(html){document.getElementById('warn').innerHTML=
  html?'<div class="warn"><span>'+html+'</span></div>':'';}
function ocEnsure(sym,then){
  if(DATA[sym]){then();return;}
  const sc=document.createElement('script');
  sc.src='tickers/'+encodeURIComponent(sym)+'.js?v='+encodeURIComponent(OC_VER[sym]||'');
  sc.onload=()=>{if(DATA[sym])then();else ocNote('Could not read the data for <b>'+sym+'</b>.');};
  sc.onerror=()=>ocNote('No data file for <b>'+sym+'</b>. Download it again.');
  document.head.appendChild(sc);
}
function ocInit(){
  const sel=document.getElementById('tsel'), list=ocList();
  if(!list.length){
    ocNote('No tickers yet. Type one into the box above and press <b>download</b>.');
    return;
  }
  sel.innerHTML=list.map(k=>'<option value="'+k+'">'+k+'</option>').join('');
  // The chosen symbol is kept in the address, so the desktop app can reload
  // the page after a download and return to the same ticker.
  const _h=decodeURIComponent((location.hash||'').slice(1)).toUpperCase();
  cur=(_h&&list.includes(_h))?_h:(list.includes(cur)?cur:list[0]);
  sel.value=cur;
  sel.onchange=()=>{const s=sel.value;
    ocEnsure(s,()=>{cur=s;yCenter=null;yShift=0;
      try{history.replaceState(null,'','#'+cur);}catch(e){}
      build();});};
  ocEnsure(cur,()=>build());
}
['d','w'].forEach(k=>{
  const b=document.getElementById('bar-'+k);
  if(b)b.onclick=()=>{barMode=k;yCenter=null;yShift=0;
    ['d','w'].forEach(j=>document.getElementById('bar-'+j)
      .setAttribute('aria-pressed',String(j===k)));
    build();};
});

EMAS.forEach((E,i)=>{
  const b=document.getElementById('ema'+i), n=document.getElementById('ema'+i+'n');
  if(!b||!n)return;
  const save=()=>{try{localStorage.setItem('oc_ema',JSON.stringify(
    EMAS.map(e=>({on:e.on,n:e.n}))));}catch(e){}};
  b.setAttribute('aria-pressed',String(E.on)); n.value=E.n;
  b.onclick=()=>{E.on=!E.on;b.setAttribute('aria-pressed',String(E.on));save();draw();};
  n.addEventListener('keydown',ev=>ev.stopPropagation());  // not a chart shortcut
  n.onchange=()=>{const v=Math.round(+n.value);
    if(v>=2&&v<=1000){E.n=v;E.on=true;b.setAttribute('aria-pressed','true');save();draw();}
    else n.value=E.n;};
});

[['tb-cone','cone'],['tb-delta','delta']].forEach(([id,m])=>{
  const b=document.getElementById(id);
  if(b)b.onclick=()=>{tableMode=m;
    [['tb-cone','cone'],['tb-delta','delta']].forEach(([j,w])=>
      document.getElementById(j).setAttribute('aria-pressed',String(w===m)));
    table();};
});

if(OC_SHELL){
  const sc=document.createElement('script');
  sc.src='tickers/index.js?t='+Date.now();  // never a cached list
  sc.onload=ocInit; sc.onerror=ocInit;  // no index yet: empty state
  document.head.appendChild(sc);
} else ocInit();
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>setTimeout(()=>{_lut=null;draw();},40));
new MutationObserver(()=>setTimeout(()=>{_lut=null;draw();},40))
  .observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
</script>"""

APP_JS = """<script>
// Wired only inside the desktop app, which exposes its Python side as
// window.pywebview.api. Elsewhere the bar stays hidden.
(function(){
  var bar=document.getElementById('appbar'); if(!bar)return;
  var api=function(){return window.pywebview&&window.pywebview.api;};
  var st=document.getElementById('ab-status'), inp=document.getElementById('ab-sym'),
      wk=document.getElementById('ab-wk'), busy=false, wired=false;
  function setBusy(b){busy=b;
    bar.querySelectorAll('button').forEach(function(x){if(x.dataset.keep!=='1')x.disabled=b;});
    inp.disabled=b;}
  function go(list){ if(busy||!api())return; setBusy(true); st.textContent='starting...';
    api().refresh(list,wk.checked,(typeof cur==='string'?cur:'')).then(function(r){
      if(!r||!r.ok){setBusy(false);st.textContent=(r&&r.msg)||'could not start';}});}
  function init(){ if(wired)return; wired=true; bar.hidden=false;
    document.getElementById('ab-add').onclick=function(){
      var s=inp.value.split(/[ ,;]+/).filter(Boolean);
      if(!s.length){st.textContent='type a ticker first';inp.focus();return;} go(s);};
    // Typing a ticker must not reach the chart's single-key shortcuts.
    inp.addEventListener('keydown',function(e){e.stopPropagation();
      if(e.key==='Enter'){e.preventDefault();document.getElementById('ab-add').click();}});
    document.getElementById('ab-all').onclick=function(){go([]);};
    document.getElementById('ab-browser').onclick=function(){api().open_in_browser();};
    document.getElementById('ab-folder').onclick=function(){api().open_data_folder();};
    api().status().then(function(s){ if(!s)return;
      if(s.busy){setBusy(true);st.textContent='working...';}
      else{st.textContent=s.note||'';st.classList.toggle('bad',!!s.alert);}});
  }
  var pb=document.getElementById('ab-prog'), pbi=pb&&pb.firstChild;
  window.ocProgress=function(line,frac){st.textContent=line;st.classList.remove('bad');
    if(pb&&frac!=null){pb.hidden=false;pbi.style.width=(Math.max(0,Math.min(1,frac))*100).toFixed(1)+'%';}};
  window.ocDone=function(ok,msg){setBusy(false);st.textContent=msg;if(pb)pb.hidden=true;};
  if(api())init(); else window.addEventListener('pywebviewready',init);
})();
</script>"""

html = (HEAD + BODY + "<script>const DATA=" + json.dumps(DATA)
        + ";const OC_SHELL=" + ("true" if APP else "false") + ";</script>"
        + SCRIPT + APP_JS)
out = sub("charts") / ("app.html" if APP else "optionscone.html")
out.write_text(html, encoding="utf-8")
print(f"{len(html)} bytes -> {out}")
