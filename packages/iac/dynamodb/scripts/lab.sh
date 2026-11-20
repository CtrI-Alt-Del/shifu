#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$LAB_DIR/../../.." && pwd)"
MODE="${1:-}"
shift || true

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_COMMAND=("$PYTHON_BIN")
elif [[ -x "$REPO_DIR/apps/server/.venv/Scripts/python.exe" ]]; then
  PYTHON_COMMAND=("$REPO_DIR/apps/server/.venv/Scripts/python.exe")
else
  PYTHON_COMMAND=(python3)
fi

if [[ -z "$MODE" ]]; then
  echo "Usage: lab.sh {load|simulate|query|metrics|validate-fixtures} [options]" >&2
  exit 2
fi

if [[ "$MODE" == "validate-fixtures" ]]; then
  exec "${PYTHON_COMMAND[@]}" "$SCRIPT_DIR/dynamodb_lab.py" "$MODE" --fixtures "$LAB_DIR/fixtures/events.json"
fi

TABLE_NAME="${TABLE_NAME:-$(terraform -chdir="$LAB_DIR" output -raw table_name)}"
PROFILE="${AWS_PROFILE:-shifu-lab}"
REGION="${AWS_REGION:-us-east-2}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$LAB_DIR/evidence-local}"

mkdir -p "$EVIDENCE_DIR"
exec "${PYTHON_COMMAND[@]}" "$SCRIPT_DIR/dynamodb_lab.py" "$MODE" \
  --table "$TABLE_NAME" \
  --profile "$PROFILE" \
  --region "$REGION" \
  --fixtures "$LAB_DIR/fixtures/events.json" \
  --evidence-dir "$EVIDENCE_DIR" \
  --responsible "${RESPONSIBLE:-Gabriel da Silva}" \
  "$@"
