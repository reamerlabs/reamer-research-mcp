# Reamer Research MCP server

<!-- mcp-name: io.github.reamerlabs/reamer-research-mcp -->

An MCP server and Claude Code plugin for
[Reamer Research](https://reamerlabs.com/products/reamer-research), a
backtesting and live trading engine for Python and C++. Your AI assistant
writes a strategy file, backtests it on your bars, reads every closed trade,
runs Monte Carlo and opens the run in visual trade diagnostics, all on your
own machine.

Works with Claude Code, Claude Desktop, Cursor and any client that speaks MCP
over stdio.

## Tools

| Tool | What it does |
|---|---|
| `engine_status` | Finds the installed engine: version, default settings, Evaluation Mode limits. |
| `api_reference` | The strategy API, order functions and every setting, for writing a strategy. |
| `backtest` | Runs a strategy file on CSV or `.bin` bars and returns the summary metrics and a `run_id`. |
| `closed_trades` | Every round trip of a run, sorted and paged. |
| `monte_carlo` | Resamples a run's per-trade returns into loss, ruin and drawdown statistics. |
| `printed_output` | Every value the strategy printed, stamped with its bar's time. |
| `open_trade_diagnostics` | Opens the run in visual trade diagnostics: each trade on its own bars, beside every value the strategy printed. |

Each backtest runs in its own process under the Python that has the engine,
so anything a strategy prints stays out of the MCP connection. Runs are
stored in `~/.cache/reamer-research-mcp/runs/` (`REAMER_MCP_RUNS` moves it),
each with the full JSON report and the trade diagnostics page.

## Install

The server installs the engine,
[`reamer-research` from PyPI](https://pypi.org/project/reamer-research/), with
itself: no download, key or sign-up. Linux x86-64, macOS on Apple silicon,
Windows through WSL2. Add it in one of these ways.

Claude Code plugin, which also adds a Reamer Research skill (needs
[uv](https://docs.astral.sh/uv/)):

```bash
claude plugin marketplace add reamerlabs/reamer-research-mcp
claude plugin install reamer-research@reamerlabs
```

Claude Code, server only:

```bash
claude mcp add reamer-research -- uvx reamer-research-mcp
```

Claude Desktop, Cursor and other clients, in the client's MCP config:

```json
{
  "mcpServers": {
    "reamer-research": {
      "command": "uvx",
      "args": ["reamer-research-mcp"]
    }
  }
}
```

Without uv, `pip install reamer-research-mcp` and use `reamer-research-mcp`
as the command.

To use an engine you installed elsewhere instead (a virtual environment with
`pip install reamer-research`, or the kit's wheel), point `REAMER_PYTHON` at
that environment's Python:

```json
"env": { "REAMER_PYTHON": "/home/you/venv/bin/python" }
```

The server needs Python 3.10 or later. The engine runs on Python 3.9 or later.

## Try it

Ask your assistant:

> Download https://raw.githubusercontent.com/reamerlabs/reamer-research-examples/main/python/sample_data/AAPL.csv,
> write an ATR band reversion strategy for Reamer Research, backtest it on
> that file with a 0.005 commission and a 0.01 spread, show me the five worst
> trades and run Monte Carlo.

## Evaluation Mode

Without a licence, each backtest runs on one ticker over at most 30 days or
50,000 bars, whichever comes first, and live trading is off. A run past a
limit returns an error that names the limit. A
[Reamer Research licence](https://reamerlabs.com/pricing) is $20 per seat per
month and removes every limit; activate it once per machine with
`bin/reamer-license` from the [full kit](https://reamerlabs.com/download), and
the same strategy files run unchanged.

## Links

- [Reamer Research](https://reamerlabs.com/products/reamer-research)
- [Documentation](https://reamerlabs.com/docs)
- [The engine on PyPI](https://pypi.org/project/reamer-research/)
- [Release page and the full kit](https://github.com/reamerlabs/reamer-research)
- [Examples](https://github.com/reamerlabs/reamer-research-examples)

## Licence

This server, the plugin and the skill are under the MIT licence. The engine
is commercial software under the Reamer Labs Software License Agreement,
installed from [PyPI](https://pypi.org/project/reamer-research/) as a dependency.

Support: open an issue at [github.com/reamerlabs/reamer-research/issues](https://github.com/reamerlabs/reamer-research/issues), or email support@reamerlabs.com (best effort).
