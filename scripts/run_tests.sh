#!/usr/bin/env bash
# Run the bundled Python / JavaScript / Java suites and the declarative Testoria specs.
#
# By default every suite runs against the bundled demo API (started on a free port).
# Pass --base-url (or set API_BASE_URL) to run the same suites against your own API.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
cd "$ROOT" || exit 2

LANGUAGES="all"
TEST_TYPE="functional"
ENV_NAME="dev"
REPORT=false
PARALLEL=false
VERBOSE=false
BASE_URL="${API_BASE_URL:-}"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; NC=$'\033[0m'
else
  RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; NC=""
fi

usage() {
  cat <<USAGE
Usage: scripts/run_tests.sh [options]

  -l, --language LIST   python, javascript, java, specs or all; comma-separated (default: all)
  -t, --type TYPE       functional, integration, security, performance or all (default: functional)
  -e, --env NAME        environment from core/config/config.json (default: dev)
  -u, --base-url URL    run against this API instead of the bundled demo API
  -r, --report          generate (and open) an Allure report if the allure CLI is installed
  -p, --parallel        run languages in parallel
  -v, --verbose         verbose output
  -h, --help            show this help
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    -l|--language) LANGUAGES="$2"; shift 2 ;;
    -t|--type) TEST_TYPE="$2"; shift 2 ;;
    -e|--env) ENV_NAME="$2"; shift 2 ;;
    -u|--base-url) BASE_URL="$2"; shift 2 ;;
    -r|--report) REPORT=true; shift ;;
    -p|--parallel) PARALLEL=true; shift ;;
    -v|--verbose) VERBOSE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "${RED}Unknown option: $1${NC}" >&2; usage; exit 2 ;;
  esac
done

case "$TEST_TYPE" in functional|integration|security|performance|all) ;; *) echo "${RED}Invalid --type: $TEST_TYPE${NC}" >&2; exit 2 ;; esac
[ "$LANGUAGES" = all ] && LANGUAGES="python,javascript,java,specs"
[ "$TEST_TYPE" = all ] && TYPES="functional integration security" || TYPES="$TEST_TYPE"

# --------------------------------------------------------------------------- python interpreter
PY=""
for c in "$ROOT/.venv/bin/python" "$ROOT/.venv/Scripts/python.exe" python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "${RED}Python 3.8+ is required (run ./install.sh)${NC}" >&2; exit 2; }
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export ENVIRONMENT="$ENV_NAME"
export TESTORIA_PYTHON="$PY"

# --------------------------------------------------------------------------- demo API
# Each language gets its own fresh demo API so suites never see each other's data.
EXTERNAL_URL="$BASE_URL"
DEMO_PIDS=()
cleanup() { for p in "${DEMO_PIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done; }
trap cleanup EXIT INT TERM

start_target() {  # sets API_BASE_URL for the current (sub)shell
  if [ -n "$EXTERNAL_URL" ]; then
    export API_BASE_URL="$EXTERNAL_URL" TESTORIA_BASE_URL="$EXTERNAL_URL"; BASE_URL="$EXTERNAL_URL"; return
  fi
  local port
  port="$("$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
  "$PY" -m testoria demo-api --port "$port" >/dev/null 2>&1 &
  DEMO_PIDS+=("$!")
  BASE_URL="http://127.0.0.1:$port"
  for _ in $(seq 1 200); do
    "$PY" -c "import urllib.request; urllib.request.urlopen('$BASE_URL/health', timeout=2)" 2>/dev/null && break
    sleep 0.3
  done
  export API_BASE_URL="$BASE_URL" TESTORIA_BASE_URL="$BASE_URL"
}

RESULTS_DIR="$ROOT/reports/allure-results"
mkdir -p "$RESULTS_DIR" "$ROOT/reports"

echo "${BOLD}Testoria suites${NC}  languages=${LANGUAGES}  type=${TEST_TYPE}  env=${ENV_NAME}  target=${EXTERNAL_URL:-bundled demo API}"

has_lang() { case ",$LANGUAGES," in *",$1,"*) return 0 ;; *) return 1 ;; esac; }

run_python() {
  local t dirs=()
  for t in $TYPES; do [ -d "tests/${t}_tests/python" ] && dirs+=("tests/${t}_tests/python"); done
  if [ "$TEST_TYPE" = performance ]; then
    "$PY" -m testoria load "$BASE_URL/health" -n 200 -u 10 --p95 2000 --max-error-rate 0.01 -o reports/load-summary.json
    return
  fi
  [ ${#dirs[@]} -gt 0 ] || { echo "${YELLOW}No Python tests for type $TEST_TYPE${NC}"; return 0; }
  local args=(-p no:cacheprovider --junitxml=reports/python-junit.xml)
  "$PY" -c 'import allure_pytest' 2>/dev/null && args+=(--alluredir "$RESULTS_DIR/python")
  [ "$VERBOSE" = true ] && args+=(-v) || args+=(-q)
  "$PY" -m pytest "${dirs[@]}" "${args[@]}"
}

run_javascript() {
  command -v node >/dev/null 2>&1 || { echo "${YELLOW}Node.js not found; skipping JavaScript${NC}"; return 0; }
  [ -d node_modules ] || { echo "${YELLOW}node_modules missing; run ./install.sh --js${NC}"; return 1; }
  local t files=()
  for t in $TYPES; do
    for f in tests/${t}_tests/javascript/test_*.js; do [ -f "$f" ] && files+=("$f"); done
  done
  if [ "$TEST_TYPE" = performance ]; then
    if command -v k6 >/dev/null 2>&1; then k6 run -e BASE_URL="$BASE_URL" --vus 5 --duration 10s tests/performance_tests/k6_scripts/api_load_test.js
    else echo "${YELLOW}k6 not installed; skipping k6 script${NC}"; fi
    return
  fi
  [ ${#files[@]} -gt 0 ] || { echo "${YELLOW}No JavaScript tests for type $TEST_TYPE${NC}"; return 0; }
  ALLURE_SUBDIR=javascript npx --no-install mocha "${files[@]}"
}

run_java() {
  command -v java >/dev/null 2>&1 || { echo "${YELLOW}Java not found; skipping Java${NC}"; return 0; }
  [ "$TEST_TYPE" = performance ] && { echo "${YELLOW}No Java performance tests${NC}"; return 0; }
  local mvn=./mvnw; [ -x ./mvnw ] || mvn=mvn
  local args=(-B -Dallure.results.directory="$RESULTS_DIR/java")
  [ "$VERBOSE" = true ] || args+=(-q)
  "$mvn" "${args[@]}" test
}

run_specs() {
  [ "$TEST_TYPE" = performance ] && return 0
  local tags=()
  [ "$TEST_TYPE" != all ] && tags=(--tag "$TEST_TYPE")
  "$PY" -m testoria run examples/demo-api --base-url "$BASE_URL" -o reports/specs ${tags[@]+"${tags[@]}"} --allow-empty -q
}

declare -a NAMES=() STATUSES=()
run_one() {
  local name="$1"
  echo ""
  echo "${BLUE}${BOLD}▶ $name${NC}"
  start_target
  [ -z "$EXTERNAL_URL" ] && echo "  demo API at $BASE_URL"
  if "run_$name"; then echo "${GREEN}✔ $name passed${NC}"; return 0
  else echo "${RED}✘ $name failed${NC}"; return 1; fi
}

if [ "$PARALLEL" = true ]; then
  declare -a PIDS=()
  for lang in python javascript java specs; do
    has_lang "$lang" || continue
    ( DEMO_PIDS=(); trap cleanup EXIT; run_one "$lang" > "reports/$lang.log" 2>&1 ) &
    PIDS+=("$!"); NAMES+=("$lang")
  done
  for i in "${!PIDS[@]}"; do
    if wait "${PIDS[$i]}"; then STATUSES+=(0); else STATUSES+=(1); fi
    cat "reports/${NAMES[$i]}.log"
  done
else
  for lang in python javascript java specs; do
    has_lang "$lang" || continue
    NAMES+=("$lang")
    if run_one "$lang"; then STATUSES+=(0); else STATUSES+=(1); fi
  done
fi

if [ "$REPORT" = true ]; then
  if command -v allure >/dev/null 2>&1; then
    allure generate "$RESULTS_DIR"/* --clean -o reports/allure-report && allure open reports/allure-report
  else
    echo "${YELLOW}allure CLI not installed; HTML report for specs is at reports/specs/report.html${NC}"
  fi
fi

echo ""
echo "${BOLD}Summary${NC}"
FAILED=0
for i in "${!NAMES[@]}"; do
  if [ "${STATUSES[$i]}" = 0 ]; then echo "  ${GREEN}✔${NC} ${NAMES[$i]}"; else echo "  ${RED}✘${NC} ${NAMES[$i]}"; FAILED=1; fi
done
exit $FAILED
