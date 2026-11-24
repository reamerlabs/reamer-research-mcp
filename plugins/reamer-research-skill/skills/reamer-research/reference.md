# Reamer Research API reference

Reamer Research is a backtesting and live trading engine for Python and C++.
`import reamer_research as rr`. Full documentation: https://reamerlabs.com/docs

## strategy

A strategy file is a Python file. It defines one of:

- a function `on_bar(data)`,
- a class with an `on_bar(self, data)` method (instantiated once with no arguments),
- an object with an `on_bar` method, configured in the file.

A class or object may set `lookback` (bars per window) and define
`on_progress(done, total)`, which stops the run by returning `True`.

```python
import numpy as np
import reamer_research as rr

class AtrBands:
    lookback = 20

    def __init__(self, k=2.0, qty=10):
        self.k, self.qty = k, qty

    def on_bar(self, d):
        c, h, l = d.close, d.high[1:], d.low[1:]
        if c[0] == 0: return                      # warm-up: the window is still filling
        atr = (np.maximum(h, c[:-1]) - np.minimum(l, c[:-1])).mean()
        mid, px, band = c.mean(), c[-1], self.k * atr
        if d.position() == 0 and px < mid - band:
            return rr.buy_market(self.qty, take_profit=mid, stop_loss=px - band)
        if d.position() == 0 and px > mid + band:
            return rr.sell_market(self.qty, take_profit=mid, stop_loss=px + band)
```

`on_bar` runs once per bar, after the bar closes. An order it returns is
eligible from the next bar onward. It returns `None`, one order or action, or
a list or tuple of them. Anything it prints (`print(f'rsi={rsi:.1f}')`) is
stored per bar and plotted beside each trade in visual trade diagnostics.

## data

Inside `on_bar(data)`, in a one-ticker run:

| Attribute | Meaning |
|---|---|
| `data.close`, `open`, `high`, `low` | float64 arrays of length `lookback`; `[-1]` is the bar that just closed, `[0]` the oldest |
| `data.volume`, `data.notional` | float64 arrays |
| `data.ts` | this step's time, epoch seconds UTC |
| `data.position(ticker=None)` | signed position: positive long, negative short, 0.0 flat |
| `data.position_state(ticker=None)` | dict: `qty`, `avg_entry_price`, `take_profit`, `stop_loss`, `unrealized_pnl`, `entry_ts` |
| `data.open_orders()` | resting orders, with their `order_id`s |
| `data.action_results()` | how last bar's actions went: `applied`, `reject_reason` |
| `data.exogenous(ticker)` | latest sidecar value at or before this bar, as bytes, or `None` |
| `data.tickers` | ticker names |

With several tickers, take a view first: `tv = data['AAPL']`, then `tv.close`,
`tv.ts` (array) and `tv.valid` (`True` if this ticker's row closed at this
step). One wall clock runs the backtest, so rows never need to line up; gate
on `tv.valid`.

## orders

```python
rr.buy_market(qty, *, ticker=None, tif='GTC', expiry_timestamp=None, take_profit=None, stop_loss=None)
rr.sell_market(qty, ...)               # same keywords
rr.buy_limit(limit_price, qty, ...)    # fills at the limit or better
rr.sell_limit(limit_price, qty, ...)
rr.buy_stop(stop_price, qty, ...)      # triggers when price reaches the stop
rr.sell_stop(stop_price, qty, ...)
rr.close_position(qty=0, *, ticker=None)   # 0 closes the whole position
rr.cancel_order(order_id, *, ticker=None)
rr.modify_order(order_id, *, price=None, take_profit=None, stop_loss=None)
rr.modify_position(*, ticker, take_profit=None, stop_loss=None)
rr.close_all()
rr.cancel_all()
```

- `take_profit` and `stop_loss` attach a bracket to any entry.
- Time in force: `'GTC'` (default), `'IOC'`, or `'GTD'` with
  `expiry_timestamp="YYYY-MM-DD HH:MM:SS"`.
- `ticker` may be left out in a one-ticker run.

## settings

Keyword arguments of `rr.backtest`, passed to the MCP `backtest` tool as
`settings`. Every cost defaults to zero.

| Setting | Default | Meaning |
|---|---|---|
| `initial_capital` | 10000.0 | starting cash |
| `leverage` | 1.0 | an entry's notional may be at most equity × leverage |
| `commission_per_unit` | 0.0 | commission per unit traded |
| `commission_mode` | `'round_trip'` | `'round_trip'`, `'open_only'` or `'close_only'` |
| `slippage` | 0.0 | fixed slippage per fill |
| `price_volatility` | 0.0 | scale of sampled slippage; can be negative per fill (price improvement) |
| `spread` | 0.0 | bid/ask spread |
| `ohlcv_type` | `'bid'` | what the bars are: `'bid'`, `'ask'` or `'midpoint'` |
| `swap_per_unit` | 0.0 | overnight financing per unit |
| `rng_seed` | 42 | seed of the tick path inside each bar; same seed, same result to the byte |
| `roll_cycle_months` | `()` | months (1 to 12) a futures roll recurs in; empty disables rolls |
| `roll_days_before_monthend` | 5 | days before month end the roll happens |
| `periods_per_year` | 0.0 | annualisation for Sharpe; 0 infers it |

`lookback`, `start` and `end` (epoch seconds UTC, inclusive) and
`ticker_config` (`{ticker: {setting: value}}`) are separate arguments.
The execution specification, https://reamerlabs.com/docs/execution-spec,
defines every setting exactly.

## data_files

`data` is a path to a `.csv` or `.bin` file, a list of paths, or
`{ticker: path}`. A ticker is named after its file (`AAPL.csv` is `AAPL`).
CSV headers are matched loosely (`Date`, `<CLOSE>`, `Timestamp`), so
MetaTrader exports work as saved. Separate date and time columns, date
strings (read as UTC) and epoch seconds, milliseconds, microseconds or
nanoseconds all work. Bars may be of any type: time, tick, volume, dollar or
your own rule. Synthetic sample bars:
https://raw.githubusercontent.com/reamerlabs/reamer-research-examples/main/python/sample_data/AAPL.csv
In Python, `rr.load_csv`, `rr.to_bars(df)`, `rr.write_bin` and
`rr.read_bin` convert data. The full kit (https://reamerlabs.com/download)
adds `python/fetchers/` for Alpaca and Databento bars.

## results

`rr.backtest` returns a result. `print(result)` shows the headline table.

- `result.summary`: a dict of metrics, including `net_pnl`, `gross_pnl`,
  `total_fees`, `total_return_pct`, `closed_trades_count`, `win_rate`,
  `profit_factor`, `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`,
  `equity_drawdown_maximal`, `equity_drawdown_relative`,
  `avg_holding_time_seconds`. Each is also an attribute.
- `result.closed_trades`: every round trip: `ticker`, `side`,
  `open_timestamp`, `close_timestamp`, `entry_price`, `exit_price`, `qty`,
  `gross_pnl`, `net_pnl`, `fees`, `slippage`, `return_pct`, `stop_loss`,
  `take_profit`.
- `result.monte_carlo(simulations=10000, seed=0)`: resamples per-trade returns
  into loss, ruin and drawdown statistics.
- `result.open_viewer()`: opens the run in visual trade diagnostics: each
  trade on its own bars, beside every value the strategy printed.
- `result.write_json(path)`: the full report, with every fill, the order log
  with reject reasons and the equity curve.

## evaluation_mode

Without a licence the engine runs in Evaluation Mode: one ticker per
backtest, over at most 30 days of bar time or 50,000 bars, whichever comes
first. Monte Carlo and visual trade diagnostics work; live trading needs a
licence. A run past a limit stops with `rr.EvaluationLimit`, which names the
limit; nothing is truncated. A licence ($20 per seat per month,
https://reamerlabs.com/pricing) removes every limit and the same code runs
unchanged. Activate it once per machine with `bin/reamer-license activate`
from the kit at https://reamerlabs.com/download.

## live

The relay (`rr.Relay`) sends the orders `on_bar` returns to an open-source
receiver that places them with your own broker. It needs a licence. See
https://reamerlabs.com/docs/research-live

## install

The MCP server installs the engine with itself (`uvx reamer-research-mcp`).
Without the server: `pip install reamer-research` (Python 3.9+), or
`pip install "reamer-research[pandas]"` for DataFrames. Linux x86-64, macOS on
Apple silicon, Windows through WSL2. No key or sign-up: it runs in Evaluation
Mode. To use an engine in another environment, set `REAMER_PYTHON` to that
environment's `python` in the server's config. The full kit
(https://reamerlabs.com/download) adds the C++ wrapper, the C ABI, data
fetchers, the paper broker and relay receiver, and `reamer-license`.
