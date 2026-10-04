# Design notes

The reasoning behind the main choices, for anyone reading or changing the
code. The Methods section in the app describes what is computed; this file
describes why.

## Touch probability, not delta

Traders often read delta as "the probability of expiring in the money". It is
not: delta is N(d1), the terminal probability is N(d2), and the gap grows with
volatility times the square root of time. On a volatile stock a 0.30 delta put
can have a terminal probability above 40%.

For a stop level or a price target, the more useful question is whether the
price gets there at all before expiry. That touch probability is roughly twice
the terminal one, and it is what the cone shows by default. Terminal
("expire") is available as the second contour kind. Delta and gamma are shown
in the tooltip and the data table only so the numbers can be checked against a
broker.

Both implied probabilities use the same risk-neutral drift, r - sigma^2/2, so
that touch is never below expire for the same contract.

## American pricing

Listed US equity options are American. Solving implied volatility with a
European formula misprices in-the-money puts and anything near a dividend, and
those errors show up as a distorted smile. Each contract is solved on a
Cox-Ross-Rubinstein tree with 160 steps, with dividends handled by the
escrowed-dividend method and Brent's method for the root. At about 25 ms per
contract a chain of several hundred contracts is solved in parallel across CPU
cores.

Only out-of-the-money contracts are used (calls above spot, puts below). Their
quotes are the liquid ones, and they carry almost no early-exercise premium, so
the result depends little on the American adjustment where it matters.

## Two independent views

The implied probabilities are risk-neutral: they describe the market's price
of the risk, not the real-world odds. The bootstrap models offer a different
view from the stock's own history:

- **Block bootstrap, 20 trading days.** Drawing single days would destroy
  volatility clustering; month-long blocks keep calm and turbulent stretches
  intact.
- **Real highs and lows.** Each simulated day carries the intraday range of
  the day it was drawn from, so a touch is observed rather than inferred from
  closing prices with a Brownian-bridge correction.
- **Drift kept.** The realized trend is part of the history, and a
  drift-free variant would double the number of lines on the chart without
  answering a different question.
- **5 and 10 years.** Two windows show how much the answer depends on which
  years are in the sample. 10,000 paths keep the counting noise (about 0.4
  percentage points near 27%) far below that sampling uncertainty.
- **One run per model.** The simulation runs once to the longest expiry and is
  read off at every shorter one, so probabilities can never fall with
  maturity.

Where the implied and historical contours diverge, the option market is
pricing a move the history did not produce, or the reverse. That difference is
the point of the chart; neither model is assumed to be right.

## Quote quality

Free option data contains stale, crossed and one-cent quotes. The checks are
split in two:

- **Hard checks** remove quotes that are impossible (ask below bid, price below
  intrinsic value, implied volatility outside 1% to 300%). Nothing impossible
  reaches the solver.
- **Soft checks** flag quotes that are doubtful (wide spread, one-cent bid,
  parity or forward inconsistency). A contract whose price fails them keeps its
  place on the chart but borrows the volatility of the nearest strike that
  passes, and its dot is drawn hollow.

Thin open interest is recorded but does not disqualify a price. The data
quality section reports the pass rate by moneyness, because a single headline
rate is dominated by deep contracts nobody reads.

Contracts with fewer than 10 days to expiry or an absolute delta below 0.05
are dropped entirely: their price is mostly tick size, and one of them can
stretch a color scale for the whole chain.

## Archive

Option quotes cannot be downloaded again later. Every chain is stored with its
market state as reported by Yahoo (regular session, pre-market, after hours,
closed), and exports use the
newest one taken during regular hours. Over time this becomes a history of the
option market for every ticker the user follows.

## Desktop app

The chart is a single HTML page drawn on a canvas with plain JavaScript, no
framework. The desktop app shows it in a native window (pywebview), and the
Python side downloads and computes in a background thread. The same page opens
in any browser.

Each ticker is exported to its own data file, loaded by the page on demand. A
download rewrites only that ticker's file, and the page itself never needs
rebuilding. Each file carries a format version; files written by an older
version are re-exported from the archive at start-up, without a new download.

## Maps for sellers

Most retail charting answers "where might the price go". A seller of options
asks something narrower: which strikes pay the most for the risk taken. Three
color modes serve that question, all built from data the app already has.

- **Time value per day.** Every contract shown is out of the money, so its
  whole price is time value, and the mid divided by the days left needs no
  model at all. It is an average over the remaining life; decay speeds up
  towards expiry. In-the-money contracts are left out on purpose: their time
  value is not the same as the out-of-the-money contract at the same strike
  (interest on the strike and dividends come on top), and their quotes are
  wider.
- **Implied vs realized.** The implied touch probability minus the 10-year bootstrap.
  Touch rather than expire, because the probability of finishing beyond a
  strike is dominated by drift, and the trend a stock happened to have over
  ten years is the least reliable thing history offers. The probability of
  reaching a level rests mainly on volatility, which persists. The bootstrap
  ignores the earnings calendar, so expiries just before a report compare
  against a history that contains earnings moves the market is not pricing.
- **Premium per unit risk.** The mid divided by the average intrinsic value at
  the worst point of each historical path before expiry. Path extremes depend
  on volatility far more than on trend, like the touch probability. The
  extremes are already sorted for the touch counts, so a running sum gives
  every strike in one binary search.

Open interest is colored by letting the strongest nearby contract win, so a
large position stays a wall instead of being averaged away. The two seller
maps are ratios and differences, where that rule would let a high value spill
over its neighbors; they are blended by inverse distance instead, so each
contract shows its own value at its own position.

## Rendering

Ten years of daily candles at a close zoom are over a hundred thousand pixels
wide, and browsers draw nothing on a canvas much larger than 32,000 pixels. The
scroll area therefore has the full width, while the canvas covers only the
visible window and is redrawn at the scroll position. The probability field is
computed for the visible window only, with everything that depends on a single
column or row precomputed once.

Wheel zoom is collected and applied once per animation frame, in proportion to
how far the wheel turned, so zooming stays smooth however fast the events
arrive.

The color ramp is re-parameterized so that perceived lightness falls linearly
with probability. Open interest and spread span orders of magnitude and use a
logarithmic scale; implied volatility stays linear.

The strike range is the same for every expiry so rows line up, and each side
reaches as far as the widest expiry on that side. A sparse expiry, typically a
quarterly with few strikes, would otherwise cut the whole chart short. Where
the data ends, the maps keep their edge values and fade to transparent, past
the last expiry and at the top and bottom of the range, so the cone never
stops on a line. Only transparency changes in those margins.
