"""MCP server for Reamer Research, a backtesting and live trading engine for
Python and C++. It lets an MCP client run backtests, read closed trades, run
Monte Carlo and open visual trade diagnostics with the engine installed on
this machine."""
import json
import os
import webbrowser
from pathlib import Path
from typing import Any, Optional, Union

try:
    from mcp.server.mcpserver import MCPServer as _Server   # mcp 2.x
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from . import __version__, engine

REFERENCE = Path(__file__).with_name('api_reference.md').read_text()

INSTRUCTIONS = f"""\
Reamer Research is a backtesting and live trading engine for Python and C++.
A strategy is a Python file defining on_bar(data) as a function, a class or an
object. Write the strategy file first, then call backtest with its path and a
data file (CSV or .bin). Read api_reference before writing a strategy; it has
the on_bar data fields, the order functions and every setting. Costs default to
zero, so pass the user's commission and spread in settings. Without a licence
the engine runs in Evaluation Mode (one ticker, at most 30 days or 50,000 bars
per backtest); a run past it returns an EvaluationLimit error naming the limit.
If engine_status reports the engine missing, tell the user to download the free
kit from {engine.DOWNLOAD} and pip install its wheel.
"""

server = _Server(name='reamer-research', instructions=INSTRUCTIONS)


def _abs(p):
    p = Path(os.path.expanduser(str(p)))
    return str(p if p.is_absolute() else Path.cwd() / p)


def _data_paths(data):
    if isinstance(data, str):
        return _abs(data), [_abs(data)]
    if isinstance(data, list):
        paths = [_abs(p) for p in data]
        return paths, paths
    resolved = {t: _abs(p) for t, p in data.items()}
    return resolved, list(resolved.values())


def _summary(outcome):
    s = outcome.get('summary') or {}
    keep = ('net_pnl', 'gross_pnl', 'total_fees', 'total_return_pct', 'closed_trades_count',
            'win_rate', 'profit_factor', 'sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
            'equity_drawdown_maximal', 'equity_drawdown_relative', 'avg_holding_time_seconds',
            'total_orders', 'filled_orders')
    head = {k: s[k] for k in keep if k in s}
    rest = {k: v for k, v in s.items() if k not in head}
    return head, rest


def _printed(d, limit=20):
    out = (d / 'stdout.txt')
    if not out.exists():
        return []
    lines = out.read_text().splitlines()
    return lines[-limit:]


def _failure(outcome, d=None):
    r = {'ok': False, 'error_type': outcome.get('error_type'), 'error': outcome.get('error')}
    if outcome.get('traceback'):
        r['traceback'] = outcome['traceback']
    if d is not None:
        printed = _printed(d)
        if printed:
            r['printed_output_tail'] = printed
    if outcome.get('error_type') == 'EvaluationLimit':
        r['note'] = ('Evaluation Mode limit. Run on one ticker over at most 30 days or 50,000 bars '
                     '(use start/end), or tell the user a licence at '
                     'https://reamerlabs.com/pricing removes every limit.')
    return r


@server.tool()
def engine_status() -> dict:
    """Check that the Reamer Research engine is installed. Returns the engine
    version, the Python it runs under, its default settings, the Evaluation
    Mode limits and where runs are stored, or install instructions."""
    info, err = engine.find_engine(refresh=True)
    if err:
        return {'installed': False, 'error': err, 'download': engine.DOWNLOAD}
    return {'installed': True, 'engine_version': info['version'], 'python': info['python'],
            'defaults': info['defaults'], 'server_version': __version__,
            'runs_dir': str(engine.runs_root()),
            'evaluation_mode': 'Without a licence: one ticker per backtest, at most 30 days of '
                               'bar time or 50,000 bars; live trading needs a licence '
                               '(https://reamerlabs.com/pricing).'}


@server.tool()
def api_reference(topic: Optional[str] = None) -> str:
    """The Reamer Research API: how to write a strategy and call it. topic is
    one of strategy, data, orders, settings, data_files, results,
    evaluation_mode, live, install; leave it out for everything. Read it before
    writing a strategy file."""
    if not topic:
        return REFERENCE
    sections = REFERENCE.split('\n## ')
    for sec in sections[1:]:
        if sec.split('\n', 1)[0].strip() == topic.strip().lower():
            return '## ' + sec
    names = [s.split('\n', 1)[0].strip() for s in sections[1:]]
    return f'No topic {topic!r}. Topics: {", ".join(names)}.'


@server.tool()
def backtest(strategy_file: str,
             data: Union[str, list[str], dict[str, str]],
             strategy_name: Optional[str] = None,
             lookback: Optional[int] = None,
             start: Optional[int] = None,
             end: Optional[int] = None,
             settings: Optional[dict[str, Any]] = None,
             ticker_config: Optional[dict[str, dict[str, Any]]] = None,
             timeout_s: int = 600) -> dict:
    """Run a Reamer Research backtest.

    strategy_file: path to a Python file defining on_bar(data) as a function,
      a class or an object (see api_reference). Relative paths resolve against
      the server's working directory.
    data: a .csv or .bin path, a list of them, or {ticker: path}. A ticker is
      named after its file.
    strategy_name: which global in the file to run, when it defines several.
    lookback: bars per on_bar window; defaults to the strategy's lookback, else 1.
    start, end: epoch seconds UTC, inclusive; only bars in that range run.
    settings: rr.backtest settings such as initial_capital, commission_per_unit,
      spread, slippage, price_volatility, leverage, rng_seed. Costs default to 0.
    ticker_config: {ticker: {setting: value}} where one ticker's costs differ.

    Returns the summary metrics and a run_id for closed_trades, monte_carlo,
    printed_output and open_trade_diagnostics."""
    strategy_path = _abs(strategy_file)
    if not Path(strategy_path).is_file():
        return {'ok': False, 'error_type': 'FileNotFoundError',
                'error': f'no strategy file at {strategy_path}'}
    resolved, paths = _data_paths(data)
    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        return {'ok': False, 'error_type': 'FileNotFoundError',
                'error': f'no data file at {", ".join(missing)}'}
    run_id, d = engine.new_run_dir()
    spec = {'strategy_file': strategy_path, 'strategy_name': strategy_name, 'data': resolved,
            'working_dir': str(Path(strategy_path).parent), 'lookback': lookback,
            'start': start, 'end': end, 'settings': settings or {},
            'ticker_config': ticker_config}
    outcome = engine.execute(d, spec, timeout_s)
    if not outcome.get('ok'):
        r = _failure(outcome, d)
        r['run_id'] = run_id
        return r
    head, rest = _summary(outcome)
    return {'ok': True, 'run_id': run_id, 'engine_version': outcome.get('engine_version'),
            'summary': head, 'other_metrics': rest, 'tickers': outcome.get('tickers'),
            'printed_output_tail': _printed(d, 10),
            'report_json': str(d / 'report.json'),
            'trade_diagnostics_html': str(d / 'trade-diagnostics.html')}


def _report(run_id):
    d = engine.run_dir(run_id)
    f = d / 'report.json'
    if not f.exists():
        raise ValueError(f'run {run_id} has no report; it did not finish')
    return d, json.loads(f.read_text())


@server.tool()
def closed_trades(run_id: str, sort_by: str = 'close_timestamp', descending: bool = False,
                  ticker: Optional[str] = None, limit: int = 50, offset: int = 0) -> dict:
    """The closed trades of a backtest run: ticker, side, open and close time,
    entry and exit price, qty, gross and net P&L, fees, slippage, return_pct,
    stop_loss, take_profit. sort_by is any of those fields (for example net_pnl
    with descending=True for the best trades). Paged by limit and offset."""
    try:
        _, rep = _report(run_id)
    except ValueError as e:
        return {'ok': False, 'error': str(e)}
    trades = rep.get('closed_trades') or []
    if ticker:
        trades = [t for t in trades if t.get('ticker') == ticker]
    if trades and sort_by not in trades[0]:
        return {'ok': False, 'error': f'no field {sort_by!r}; fields: {", ".join(trades[0])}'}
    trades = sorted(trades, key=lambda t: (t.get(sort_by) is None, t.get(sort_by)),
                    reverse=descending)
    limit = max(1, min(int(limit), 500))
    return {'ok': True, 'total': len(trades), 'offset': offset,
            'trades': trades[offset:offset + limit]}


@server.tool()
def monte_carlo(run_id: str, simulations: int = 10000, seed: int = 0,
                timeout_s: int = 600) -> dict:
    """Monte Carlo on a backtest run: resamples its per-trade returns into
    loss, ruin and maximum-drawdown statistics. Reruns the stored backtest,
    which gives the same trades to the byte, then simulates."""
    try:
        d = engine.run_dir(run_id)
    except ValueError as e:
        return {'ok': False, 'error': str(e)}
    spec = json.loads((d / 'spec.json').read_text())
    spec.update(monte_carlo_simulations=int(simulations), monte_carlo_seed=int(seed))
    _, mc_dir = engine.new_run_dir()
    outcome = engine.execute(mc_dir, spec, timeout_s)
    if not outcome.get('ok'):
        return _failure(outcome, mc_dir)
    return {'ok': True, 'run_id': run_id, 'simulations': simulations, 'seed': seed,
            'monte_carlo': outcome.get('monte_carlo')}


@server.tool()
def printed_output(run_id: str, limit: int = 200, offset: int = 0) -> dict:
    """What the strategy printed during a run, one JSON line per print,
    stamped with the bar's time. Use it to see the values behind each
    decision."""
    try:
        d = engine.run_dir(run_id)
    except ValueError as e:
        return {'ok': False, 'error': str(e)}
    f = d / 'console.jsonl'
    lines = f.read_text().splitlines() if f.exists() else []
    if not lines:
        lines = _printed(d, 10 ** 9)
    limit = max(1, min(int(limit), 2000))
    return {'ok': True, 'total': len(lines), 'offset': offset,
            'lines': lines[offset:offset + limit]}


@server.tool()
def open_trade_diagnostics(run_id: str, open_browser: bool = True) -> dict:
    """Open a run in visual trade diagnostics, a page that charts every closed
    trade on its own bars beside every value the strategy printed, with the
    console lines for each bar and a Monte Carlo simulation. Returns the
    page's path; opens it in the browser unless open_browser is False."""
    try:
        d = engine.run_dir(run_id)
    except ValueError as e:
        return {'ok': False, 'error': str(e)}
    page = d / 'trade-diagnostics.html'
    if not page.exists():
        return {'ok': False, 'error': f'run {run_id} has no trade diagnostics page'}
    opened = False
    if open_browser:
        try:
            opened = webbrowser.open(page.as_uri())
        except Exception:
            opened = False
    return {'ok': True, 'path': str(page), 'url': page.as_uri(), 'opened': opened}


def main():
    server.run()


if __name__ == '__main__':
    main()
