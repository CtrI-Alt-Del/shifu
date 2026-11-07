#!/usr/bin/env bash
# Run `alembic upgrade head` once as a Fargate task and fail unless it exits 0.
#
# Usage: run-migration.sh <cluster> <task-definition-arn> <subnet-ids> <security-group-id> <log-group>
#
# <subnet-ids> is comma separated. Staging has no NAT Gateway, so the task gets a
# public IP to reach ECR, Secrets Manager and CloudWatch Logs.
set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "usage: $0 <cluster> <task-definition-arn> <subnet-ids> <security-group-id> <log-group>" >&2
  exit 64
fi

cluster="$1"
task_definition="$2"
subnets="$3"
security_group="$4"
log_group="$5"

network="awsvpcConfiguration={subnets=[${subnets}],securityGroups=[${security_group}],assignPublicIp=ENABLED}"
overrides='{"containerOverrides":[{"name":"server","command":["alembic","upgrade","head"]}]}'

started="$(aws ecs run-task \
  --cluster "${cluster}" \
  --task-definition "${task_definition}" \
  --launch-type FARGATE \
  --network-configuration "${network}" \
  --overrides "${overrides}" \
  --count 1 \
  --output json)"

task_arn="$(jq -r '.tasks[0].taskArn // empty' <<<"${started}")"
if [[ -z "${task_arn}" ]]; then
  echo "The migration task did not start:" >&2
  jq '.failures' <<<"${started}" >&2
  exit 1
fi

task_id="${task_arn##*/}"
echo "Migration task started: ${task_id}"

aws ecs wait tasks-stopped --cluster "${cluster}" --tasks "${task_arn}"

result="$(aws ecs describe-tasks \
  --cluster "${cluster}" \
  --tasks "${task_arn}" \
  --query 'tasks[0].{exitCode: containers[?name==`server`] | [0].exitCode, stopCode: stopCode, stoppedReason: stoppedReason}' \
  --output json)"
exit_code="$(jq -r '.exitCode // "none"' <<<"${result}")"

echo "--- migration log (last 60 lines) ---"
aws logs get-log-events \
  --log-group-name "${log_group}" \
  --log-stream-name "server/server/${task_id}" \
  --limit 60 \
  --query 'events[].message' \
  --output text 2>/dev/null || echo "(no log events found)"
echo "-------------------------------------"

if [[ "${exit_code}" != "0" ]]; then
  echo "Migration failed. Exit code: ${exit_code}. Result: ${result}" >&2
  exit 1
fi

echo "Migration finished with exit code 0."
