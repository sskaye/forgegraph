"""Run Forgemark's pinned command-line tool (see forgegraph.forgemark).

uv run python scripts/forgemark.py lint review/phase-02/recreations.html
"""

import sys

from forgegraph.forgemark import run

result = run(*sys.argv[1:], check=False)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
raise SystemExit(result.returncode)
