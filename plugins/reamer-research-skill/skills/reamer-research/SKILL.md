---
name: reamer-research
description: Write, backtest and debug trading strategies with Reamer Research, a backtesting and live trading engine for Python and C++. Use when the user wants to backtest a strategy, port one from Backtrader, NautilusTrader or QuantConnect LEAN, check trades in visual trade diagnostics, run Monte Carlo, or mentions reamer_research or Reamer Research.
---

# Reamer Research

Reamer Research is a backtesting and live trading engine for Python and C++
(`import reamer_research as rr`, or `#include <reamer_research.hpp>`). Each bar
is replayed as a seeded tick path, so stops, targets and limits fill inside
the bar, and the same data, settings and seed give the same result to the
byte.

## Workflow

1. Check the engine: run `python3 -c "import reamer_research"` with the
   Python the user works in. If it is missing, install it with
   `pip install reamer-research` (Linux x86-64, macOS on Apple silicon,
   Windows through WSL2; Python 3.9+). No key or sign-up is needed.
2. Read [reference.md](reference.md) before writing code.
3. Write the strategy to a `.py` file in the user's project: an `on_bar(data)`
   function, a class with `on_bar(self, data)` and a `lookback` attribute, or
   an object. Prefer a class when the strategy keeps state or has parameters.
   `print()` the values behind each decision (`print(f'rsi={rsi:.1f}')`):
   visual trade diagnostics plots them beside every trade.
4. Backtest it from a small script that calls
   `rr.backtest(Strategy, 'data.csv', ...)` and prints the result. Pass the
   user's costs (`commission_per_unit`, `spread`, `slippage`,
   `initial_capital`); every cost defaults to zero, so say so when reporting a
   frictionless run.
5. Report the summary: net P&L, return, closed trades, win rate, profit
   factor, Sharpe, maximum drawdown. Show the best and worst closed trades,
   use the printed values to explain a decision, and run Monte Carlo for the
   spread of outcomes.
6. Offer visual trade diagnostics (`result.open_viewer()`) so the user can
   check each trade on its bars.

If the reamer-research MCP server is connected, its tools do steps 1 to 6:
`engine_status`, `api_reference`, `backtest`, `closed_trades`,
`printed_output`, `monte_carlo` and `open_trade_diagnostics`. Its setup is at
https://reamerlabs.com/docs/research-mcp

## Rules of the engine

- An order returned from `on_bar` is eligible from the next bar onward.
- Early bars of the window are zero while it fills: guard with
  `if data.close[0] == 0: return`.
- `data.close[-1]` is the bar that just closed.
- `data.position()` is signed; `rr.close_position()` closes the whole position.
- `take_profit=` and `stop_loss=` on any entry attach a bracket; there are no
  child orders to manage.
- With several tickers, read `tv = data['AAPL']` and gate on `tv.valid`.
- Bars may be of any type: time, tick, volume, dollar or the user's own rule.

## Evaluation Mode

Without a licence each backtest runs on one ticker over at most 30 days of bar
time or 50,000 bars, and live trading is off. A run past a limit stops with an
error that names the limit; nothing is truncated. Narrow the run to a shorter
window or one data file. A licence at https://reamerlabs.com/pricing ($20 per
seat per month) removes every limit and the same code runs unchanged. Do not
try to work around the limits.

## Porting from another engine

- Backtrader: https://reamerlabs.com/faq/port-backtrader-strategy
- NautilusTrader: https://reamerlabs.com/faq/port-nautilustrader-strategy
- QuantConnect LEAN: https://reamerlabs.com/faq/port-quantconnect-lean-algorithm

Full documentation: https://reamerlabs.com/docs. Examples:
https://github.com/reamerlabs/reamer-research-examples
