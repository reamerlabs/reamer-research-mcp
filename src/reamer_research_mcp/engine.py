"""Finds the Reamer Research engine and runs backtests through it.

The engine is a wheel from the Reamer Research kit (reamerlabs.com/download),
installed into some Python environment. This server may run in another one
(uvx gives it its own), so the engine's interpreter is found separately:

1. REAMER_PYTHON, if set: the path of a Python that has reamer_research.
2. The interpreter running this server, if reamer_research imports there.
3. python3, then python, on PATH.

Every backtest runs in a child process of that interpreter, so a strategy's
prints, a crash or an endless loop never reach the MCP connection.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

RUNNER = Path(__file__).with_name('_runner.py')
DOWNLOAD = 'https://reamerlabs.com/download'
PROBE = ('import json, sys, reamer_research as rr; '
         'print(json.dumps({"version": getattr(rr, "__version__", ""), '
         '"abi": getattr(rr, "REAMER_ABI_VERSION", None), "python": sys.executable, '
         '"defaults": {k: (list(v) if isinstance(v, tuple) else v) for k, v in rr.DEFAULTS.items()}}))')

NOT_FOUND = (
    'Reamer Research is not installed in any Python this server can find. '
    f'Download the kit (free, no key) from {DOWNLOAD}, then install its wheel: '
    'pip install research-kit-*/python/reamer_research-*.whl. '
    'If it is installed in a virtual environment, set REAMER_PYTHON to that '
    "environment's python (for example ~/venv/bin/python) in this MCP server's config."
)


def runs_root():
    root = os.environ.get('REAMER_MCP_RUNS')
    if root:
        return Path(root).expanduser()
    base = os.environ.get('XDG_CACHE_HOME') or Path.home() / '.cache'
    return Path(base) / 'reamer-research-mcp' / 'runs'


def _candidates():
    env = os.environ.get('REAMER_PYTHON', '').strip()
    if env:
        yield os.path.expanduser(env)
        return
    yield sys.executable
    for name in ('python3', 'python'):
        found = shutil.which(name)
        if found:
            yield found


_found = None


def find_engine(refresh=False):
    """(info dict, None) for the first interpreter with reamer_research, else (None, message)."""
    global _found
    if _found and not refresh:
        return _found, None
    tried = []
    for py in _candidates():
        if py in tried:
            continue
        tried.append(py)
        try:
            p = subprocess.run([py, '-c', PROBE], capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if p.returncode == 0 and p.stdout.strip():
            _found = json.loads(p.stdout.strip().splitlines()[-1])
            return _found, None
    return None, NOT_FOUND + f' Tried: {", ".join(tried) or "none"}.'


def new_run_dir():
    run_id = time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
    d = runs_root() / run_id
    d.mkdir(parents=True, exist_ok=False)
    return run_id, d


def run_dir(run_id):
    if not run_id or '/' in run_id or '\\' in run_id or run_id.startswith('.'):
        raise ValueError(f'unknown run_id {run_id!r}')
    d = runs_root() / run_id
    if not (d / 'spec.json').exists():
        raise ValueError(f'unknown run_id {run_id!r}; run backtest first')
    return d


def execute(d, spec, timeout_s):
    """Run the spec in d with the engine's interpreter; return the outcome dict."""
    info, err = find_engine()
    if err:
        return {'ok': False, 'error_type': 'EngineNotFound', 'error': err}
    (d / 'spec.json').write_text(json.dumps(spec, indent=1))
    try:
        p = subprocess.run([info['python'], str(RUNNER), str(d)], capture_output=True,
                           text=True, timeout=timeout_s, cwd=spec['working_dir'])
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error_type': 'Timeout',
                'error': f'the backtest ran past {timeout_s} s and was stopped; '
                         'raise timeout_s or run fewer bars'}
    outcome_file = d / 'outcome.json'
    if not outcome_file.exists():
        return {'ok': False, 'error_type': 'RunnerFailed',
                'error': (p.stderr or p.stdout or 'no output')[-2000:]}
    outcome = json.loads(outcome_file.read_text())
    native = (p.stdout + p.stderr).strip()
    if native:  # lines the engine wrote straight to the process's stdout or stderr
        with open(d / 'stdout.txt', 'a') as f:
            f.write(native + '\n')
    return outcome
