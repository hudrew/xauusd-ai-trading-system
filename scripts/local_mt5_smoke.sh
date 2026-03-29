#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "Missing virtual environment python: ${VENV_PYTHON}" >&2
  exit 1
fi

PYTHONPATH="${ROOT_DIR}/src" "${VENV_PYTHON}" -m xauusd_ai_system.cli smoke

cat <<EOF

Next steps:
1. Open MT5 terminal and follow:
   ${ROOT_DIR}/docs/implementation/local_mt5_manual_debug_checklist.md
2. Record findings in:
   ${ROOT_DIR}/docs/implementation/local_mt5_debug_report_template.md
EOF
