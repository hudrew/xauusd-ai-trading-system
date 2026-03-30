#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

CSV_PATH="${1:-${ROOT_DIR}/tmp/xauusd_m1_history_100000.csv}"
OUTPUT_PATH="${2:-${ROOT_DIR}/tmp/research_pullback_sell_v3_probe_acceptance_latest.json}"
CONFIG_PATH="${ROOT_DIR}/configs/mvp_pullback_sell_research_v3_branch_gate.yaml"
REPORT_DIR="${ROOT_DIR}/reports/research_pullback_sell_v3_probe"

ensure_venv
run_cli "${CONFIG_PATH}" acceptance "${CSV_PATH}" --report-dir "${REPORT_DIR}" "${@:3}"
PYTHONPATH="${ROOT_DIR}/src" "${VENV_PYTHON}" -m xauusd_ai_system.cli report-export "${OUTPUT_PATH}" --report-dir "${REPORT_DIR}"
