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

**1. The engine.** Download the Reamer Research kit (free, no key, Linux
x86-64, macOS on Apple silicon, Windows through WSL2) from
[reamerlabs.com/download](https://reamerlabs.com/download), then:

```bash
tar xzf research-kit-*.tar.gz
pip install research-kit-*/python/reamer_research-*.whl
```

**2. The server**, in one of these ways.

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

The server finds the engine in `REAMER_PYTHON` if set, else in its own
Python, else in `python3` on `PATH`. If you installed the wheel into a
virtual environment, point `REAMER_PYTHON` at it:

```json
"env": { "REAMER_PYTHON": "/home/you/venv/bin/python" }
```

The server needs Python 3.10 or later. The engine runs on Python 3.9 or later.

## Try it

Ask your assistant:

> Write an ATR band reversion strategy for Reamer Research, backtest it on
> research-kit-4.11.3-linux_x86_64/python/sample_data/SAMPLE_5min.csv with a
> 0.005 commission and a 0.01 spread, show me the five worst trades and run
> Monte Carlo.

## Evaluation Mode

Without a licence, each backtest runs on one ticker over at most 30 days or
50,000 bars, whichever comes first, and live trading is off. A run past a
limit returns an error that names the limit. A
[Reamer Research licence](https://reamerlabs.com/pricing) is $20 per seat per
month and removes every limit; the same strategy files run unchanged.

## Links

- [Reamer Research](https://reamerlabs.com/products/reamer-research)
- [Documentation](https://reamerlabs.com/docs)
- [Release page and downloads](https://github.com/reamerlabs/reamer-research)
- [Examples](https://github.com/reamerlabs/reamer-research-examples)

## Licence

This server, the plugin and the skill are under the MIT licence. The engine
is commercial software under the Reamer Labs Software License Agreement,
downloaded separately from [reamerlabs.com/download](https://reamerlabs.com/download).

Support: support@reamerlabs.com
