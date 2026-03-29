#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

ENV_FILE="${1:-${DEFAULT_ENV_FILE}}"
OUTPUT_PATH="${2:-${ROOT_DIR}/tmp/xauusd_mt5_history.csv}"

ensure_venv
load_env_file "${ENV_FILE}"
CONFIG_PATH="$(resolve_mt5_config)"
run_cli "${CONFIG_PATH}" export-mt5-history "${OUTPUT_PATH}" "${@:3}"
