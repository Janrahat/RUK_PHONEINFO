#!/usr/bin/env bash
#
# Run the RUK_PHONEINFO test suite.
#
#   bash run_tests.sh            # unit + smoke tests
#   bash run_tests.sh units      # unit tests only (no sockets)
#   bash run_tests.sh smoke      # smoke tests only
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${HERE}"

MODE="${1:-all}"
export NO_COLOR=1
export RUK_ACCEPT_TERMS=1
export HOME="${HOME:-/tmp}"

c_reset='\033[0m'; c_cyan='\033[38;5;80m'; c_green='\033[38;5;114m'
c_red='\033[38;5;203m'

printf '%b\n' "${c_cyan}[*]${c_reset} Syntax check"
python3 -m compileall -q ruk_phoneinfo app.py tests
printf '%b\n' "${c_green}[+]${c_reset} Syntax OK"

echo
case "${MODE}" in
  units)
    printf '%b\n' "${c_cyan}[*]${c_reset} Unit tests"
    python3 -m unittest tests.test_units -v
    ;;
  smoke)
    printf '%b\n' "${c_cyan}[*]${c_reset} Smoke tests"
    python3 -m unittest tests.test_smoke -v
    ;;
  *)
    printf '%b\n' "${c_cyan}[*]${c_reset} Full test suite"
    python3 -m unittest discover -s tests -p 'test_*.py' -v
    ;;
esac

echo
printf '%b\n' "${c_green}[+]${c_reset} Tests finished"
