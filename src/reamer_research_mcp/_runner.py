"""Runs one Reamer Research backtest for the MCP server, in its own process.

    python _runner.py <run_dir>

The server writes <run_dir>/spec.json and starts this file with the Python
interpreter that has reamer_research installed, which need not be the one the
server runs in. Everything the strategy prints goes to <run_dir>/stdout.txt,
never to the server's stdio, which carries the MCP protocol. The outcome is
written to <run_dir>/outcome.json.

Only the standard library and reamer_research are imported here, so this file
runs in any environment the engine is installed in.
"""
import contextlib
import inspect
import io
import json
import os
import runpy
import sys
import traceback
from pathlib import Path


def _load_strategy(path, name):
    """The strategy in a Python file: the global called `name`, else a
    module-level on_bar function, else the one class or object defined there
    with an on_bar method."""
    module = runpy.run_path(str(path), run_name='__reamer_strategy__')
    if name:
        if name not in module:
            raise ValueError(f'{path.name} defines no {name!r}')
        return module[name]
    if callable(module.get('on_bar')) and inspect.isfunction(module['on_bar']):
        return module['on_bar']
    found = []
    for key, value in module.items():
        if key.startswith('_') or not hasattr(value, 'on_bar'):
            continue
        if inspect.isclass(value) and value.__module__ != '__reamer_strategy__':
            continue  # imported, e.g. a base class
        found.append(key)
    if len(found) == 1:
        return module[found[0]]
    if not found:
        raise ValueError(f'{path.name} defines no on_bar function and no class or object with '
                         'an on_bar method')
    raise ValueError(f'{path.name} defines several strategies ({", ".join(found)}); '
                     'pass strategy_name to pick one')


def _bars(data, base):
    def resolve(p):
        p = Path(os.path.expanduser(p))
        return str(p if p.is_absolute() else base / p)
    if isinstance(data, str):
        return resolve(data)
    if isinstance(data, list):
        return [resolve(p) for p in data]
    return {ticker: resolve(p) for ticker, p in data.items()}


def main():
    run_dir = Path(sys.argv[1])
    spec = json.loads((run_dir / 'spec.json').read_text())
    outcome = {'ok': False}
    out = io.StringIO()
    try:
        import reamer_research as rr
        outcome['engine_version'] = getattr(rr, '__version__', '')
        base = Path(spec['working_dir'])
        os.chdir(base)
        sys.path.insert(0, str(Path(spec['strategy_file']).parent))
        kwargs = dict(spec.get('settings') or {})
        for key in ('lookback', 'start', 'end', 'ticker_config'):
            if spec.get(key) is not None:
                kwargs[key] = spec[key]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            strategy = _load_strategy(Path(spec['strategy_file']), spec.get('strategy_name'))
            result = rr.backtest(strategy, _bars(spec['data'], base),
                                 result_json=str(run_dir / 'report.json'),
                                 console_log=str(run_dir / 'console.jsonl'),
                                 viewer_html=str(run_dir / 'trade-diagnostics.html'),
                                 **kwargs)
            mc = None
            if spec.get('monte_carlo_simulations'):
                mc = result.monte_carlo(simulations=int(spec['monte_carlo_simulations']),
                                        seed=int(spec.get('monte_carlo_seed') or 0))
        outcome.update(ok=True, summary=result.summary,
                       tickers=sorted({t['ticker'] for t in result.closed_trades}),
                       monte_carlo=mc)
    except Exception as e:  # reported to the client, never raised into the server
        kind = type(e).__name__
        outcome.update(error_type=kind, error=str(e))
        if kind not in ('EvaluationLimit', 'ValueError', 'FileNotFoundError'):
            outcome['traceback'] = traceback.format_exc(limit=8)
    (run_dir / 'stdout.txt').write_text(out.getvalue())
    (run_dir / 'outcome.json').write_text(json.dumps(outcome, default=str))


if __name__ == '__main__':
    main()
