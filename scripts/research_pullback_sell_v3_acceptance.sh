#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

CSV_PATH="${1:-${ROOT_DIR}/tmp/xauusd_m1_history_100000.csv}"
CONFIG_PATH="${ROOT_DIR}/configs/mvp_pullback_sell_research_v3_branch_gate.yaml"
REPORT_DIR="${ROOT_DIR}/reports/research_pullback_sell_v3"

ensure_venv
run_cli "${CONFIG_PATH}" acceptance "${CSV_PATH}" --report-dir "${REPORT_DIR}" "${@:2}"
