# OptionsCone

Probability, premium and positioning heatmaps for any stock with options.

OptionsCone turns the option chain into heatmaps on the price chart: touch and
expiry probabilities, implied volatility, open interest, spreads, time value
and premium relative to risk. It compares what the option market implies with
what the stock realized over the last five and ten years.

**Website, manual and methods: https://nikkn.github.io/OptionsCone/**

<table>
<tr>
<td width="50%" valign="top"><a href="docs/img/avgo/chart-p.png"><img src="docs/img/avgo/cone-p.png" width="300" alt="Broadcom (AVGO), Touch probability: dark near the money, fading where a touch becomes unlikely."></a><br>
<b>Touch probability</b><br>
The chance that the price touches each strike before that expiry, from the option prices: dark near the money, fading where a touch becomes unlikely.</td>
<td width="50%" valign="top"><a href="docs/img/avgo/chart-iv.png"><img src="docs/img/avgo/cone-iv.png" width="300" alt="Broadcom (AVGO), Implied volatility per contract: skew and term structure."></a><br>
<b>Implied volatility</b><br>
Each contract's own volatility, so skew and the term structure show at a glance. The badges above each expiry give its model-free volatility.</td>
</tr>
<tr>
<td width="50%" valign="top"><a href="docs/img/avgo/chart-oi.png"><img src="docs/img/avgo/cone-oi.png" width="300" alt="Broadcom (AVGO), Open interest: where the large positions sit."></a><br>
<b>Open interest</b><br>
Where the large positions sit, on a logarithmic scale so both small and large strikes stay readable.</td>
<td width="50%" valign="top"><a href="docs/img/avgo/chart-tv.png"><img src="docs/img/avgo/cone-tv.png" width="300" alt="Broadcom (AVGO), Time value per remaining day, darkest near the money for short expiries."></a><br>
<b>Time value per day</b><br>
The option price divided by the days left, an average over the remaining life. Every contract shown is out of the money, so its whole price is time value.</td>
</tr>
<tr>
<td width="50%" valign="top"><a href="docs/img/avgo/chart-gap.png"><img src="docs/img/avgo/cone-gap.png" width="300" alt="Broadcom (AVGO), Implied minus realized touch probability: blue where the market prices in a higher probability than the stock realized, red where lower."></a><br>
<b>Implied vs realized</b><br>
The market's touch probability minus how often 10,000 paths simulated from the stock's last ten years touch the strike. Blue where the market prices in a higher probability (a potential opportunity for sellers), red where lower.</td>
<td width="50%" valign="top"><a href="docs/img/avgo/chart-vpr.png"><img src="docs/img/avgo/cone-vpr.png" width="300" alt="Broadcom (AVGO), Option price relative to the average worst intrinsic value on the historical paths."></a><br>
<b>Premium per unit risk</b><br>
The option price divided by the average worst-case depth in the money across 10,000 paths simulated from the stock's last ten years. Higher means more premium per dollar of realized risk.</td>
</tr>
</table>

![OptionsCone showing Broadcom (AVGO)](docs/screenshot.png)

Each dot is a listed contract. The color behind it is the probability that
the price touches that strike before that expiry. The contour lines follow a
chosen probability (30% by default) through the expiries, once for each of
three models:

- **implied**: from the option prices themselves, with each contract's own
  implied volatility
- **5y** and **10y**: a block bootstrap of the stock's own daily history over
  the last five or ten years

Where the market and what the stock realized disagree, the lines separate.

The cone can also be colored by implied volatility, open interest, bid-ask
spread, time value per day, implied vs realized touch probability, or the
premium per dollar of realized risk. Hovering a contract shows its
probabilities, quote, delta and gamma; clicking it keeps its numbers on screen
while you switch maps. A data table lists the values for the whole chain, and
the Methods section in the app explains every number.

## Download

Windows: download `OptionsCone.exe` from the
[Releases](https://github.com/nikkn/OptionsCone/releases) page and run it. No
installation is needed.

The executable is not code-signed, so Windows SmartScreen may warn on the first
start. Click **More info**, then **Run anyway**.

## Use

Type a ticker (for example `AAPL`) and press **download**. The first download
of a ticker takes a minute or two: the option chain is fetched, every contract
is priced on a binomial tree, and 10,000 bootstrap paths are simulated per
model. **refresh all** downloads a fresh chain for every ticker already held.

Every download is archived on your computer, so a history of option chains
builds up over time. **data folder** opens it; the packaged app keeps its data
in `%LOCALAPPDATA%\OptionsCone`.

Option quotes are only meaningful while the US market is open. Outside trading
hours the app uses the newest download taken during the session.

Chart controls: drag to pan, Ctrl or Shift + scroll wheel to zoom, **reset**
to return to the full view. F toggles fullscreen.

## Run from source

Python 3.11 or later.

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Run from source, all data is written into the project folder. Set
`OPTIONSCONE_HOME` to put it elsewhere.

`python app.py --selftest AAPL` runs the whole pipeline once without a window
and writes the result to the log.

## Build the executable

```
pip install -r requirements.txt -r requirements-build.txt
python build_exe.py
```

The result is `dist/OptionsCone.exe`. Build in a clean virtual environment:
PyInstaller bundles everything installed, so a crowded environment makes the
executable several times larger. The build also writes
`THIRD_PARTY_LICENSES.txt` with the licenses of all bundled libraries.

PyInstaller does not cross-compile. A macOS build has to be made on a Mac and
has not been tested.

## Project layout

```
app.py                  desktop window, download pipeline, progress
build_exe.py            packaging
charts/export_data.py   probabilities, bootstrap and per-ticker data files
charts/build_chart.py   the chart page (HTML, CSS and JavaScript in one file)
src/american.py         binomial tree, implied volatility, Greeks
src/barrier.py          closed-form touch probabilities
src/montecarlo.py       block bootstrap with daily highs and lows
src/chain.py            option chain download and pricing
src/quality.py          quote quality checks
src/varswap.py          model-free implied volatility per expiry
src/archive.py          storage of every downloaded chain
```

[DESIGN.md](DESIGN.md) explains the main modelling and engineering decisions.

## Data

Market data comes from Yahoo Finance through the
[yfinance](https://github.com/ranaroussi/yfinance) library and is fetched
directly by your computer. OptionsCone is not affiliated with or endorsed by
Yahoo. Yahoo's data is intended for personal use; check its terms before using
it for anything else. Quotes are delayed and can be incomplete or wrong. The
quality checks catch much of that, not all of it.

## Disclaimer

All probabilities are estimates, derived from option prices or from past
returns. They are not forecasts and not financial advice. Use at your own risk.

## Contact

Bug reports and suggestions: open an
[issue](https://github.com/nikkn/OptionsCone/issues) or write to
contact.aquart@gmail.com.

## License

Copyright (C) 2026 Nikolai Alexander

OptionsCone is free software under the
[GNU Affero General Public License v3.0](LICENSE) or later. You may use, study,
modify and share it. If you distribute a modified version, or offer it to
others over a network, you must publish its source code under the same
license.
