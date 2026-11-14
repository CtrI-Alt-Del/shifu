#!/usr/bin/env bash
# Run `alembic upgrade head` once as a Fargate task and fail unless it exits 0.
#
# Usage: run-migration.sh <cluster> <task-definition-arn> <subnet-ids> <security-group-id> <log-group>
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "usage: $0 <cluster> <task-definition-arn> <subnet-ids> <security-group-id> <log-group>" >&2
  exit 64
fi

exec "$(dirname "$0")/run-server-task.sh" "$@" "database migration" -- alembic upgrade head
