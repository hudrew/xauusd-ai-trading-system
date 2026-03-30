#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/_mt5_common.sh"

ENV_FILE="${1:-${DEFAULT_ENV_FILE}}"

ensure_venv
load_env_file "${ENV_FILE}"
CONFIG_PATH="$(resolve_mt5_config "" "prod")"
run_cli "${CONFIG_PATH}" live-loop --require-deploy-gate --require-preflight "${@:2}"
