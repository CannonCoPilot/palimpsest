#!/usr/bin/env bash
# Palimpsest test runner — subcommand dispatcher.
#
# Backend tests (pytest) live in core/ and run against core/.venv (3.12). The
# pyproject there parallelizes by default (-n auto --dist=loadscope) and registers
# the markers used below. Frontend tests (vitest) live in browser/.
#
# Usage: ./run_tests.sh [command] [extra args forwarded to the runner]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/core"
BROWSER_DIR="$SCRIPT_DIR/browser"
PYTEST="$CORE_DIR/.venv/bin/python -m pytest"

# Coverage gate: the run fails if package coverage drops below this. Bump it as
# coverage improves so it can only ratchet up, never regress. Baseline is 70.9%;
# set just below it to tolerate the ~0.7% swing from the external (Ollama) test
# not running when the service is down.
COV_GATE=70

usage() {
    cat <<'EOF'
Palimpsest test runner

Backend (pytest, in core/):
  all       Whole suite, parallel (default)
  fast      Dev loop: skip slow + external  (-m "not slow and not external")
  unit      Pure-function tests only         (-m unit)
  nlp       spaCy / integration tests        (-m nlp)
  api       FastAPI server tests             (-m api)
  cli       CLI tests                        (-m cli)
  slow      The slow end-to-end outliers     (-m slow)
  changed   Only tests affected by your working-tree changes (testmon, serial)
  cov       Coverage report + gate (term-missing)
  serial    Whole suite, single process (-n0), for debugging

Frontend (vitest, in browser/):
  ui        Run the frontend suite
  ui-cov    Frontend coverage

Extra args pass through to the runner, e.g.:
  ./run_tests.sh unit -k entity -x
  ./run_tests.sh fast tests/test_tracks.py
EOF
}

cmd="${1:-all}"
if [ $# -gt 0 ]; then shift; fi

case "$cmd" in
    all)     cd "$CORE_DIR" && exec $PYTEST "$@" ;;
    fast)    cd "$CORE_DIR" && exec $PYTEST -m "not slow and not external" "$@" ;;
    unit)    cd "$CORE_DIR" && exec $PYTEST -m unit "$@" ;;
    nlp)     cd "$CORE_DIR" && exec $PYTEST -m nlp "$@" ;;
    api)     cd "$CORE_DIR" && exec $PYTEST -m api "$@" ;;
    cli)     cd "$CORE_DIR" && exec $PYTEST -m cli "$@" ;;
    slow)    cd "$CORE_DIR" && exec $PYTEST -m slow "$@" ;;
    # testmon tracks which tests cover which code; -n0 because it is incompatible
    # with xdist distribution (overrides the -n auto from pyproject addopts).
    changed) cd "$CORE_DIR" && exec $PYTEST --testmon -n0 "$@" ;;
    cov)     cd "$CORE_DIR" && exec $PYTEST --cov=palimpsest --cov-report=term-missing --cov-fail-under="$COV_GATE" "$@" ;;
    serial)  cd "$CORE_DIR" && exec $PYTEST -n0 "$@" ;;
    ui)      cd "$BROWSER_DIR" && exec npm test ;;
    ui-cov)  cd "$BROWSER_DIR" && exec npm run test:coverage ;;
    -h|--help|help) usage ;;
    *) echo "Unknown command: $cmd" >&2; echo; usage; exit 2 ;;
esac
