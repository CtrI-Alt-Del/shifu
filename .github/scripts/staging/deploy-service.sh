#!/usr/bin/env bash
# Point an ECS service at a task definition and wait for the rollout to finish.
#
# Usage: deploy-service.sh <cluster> <service> <task-definition-arn>
#
# `aws ecs wait services-stable` also succeeds after the circuit breaker rolled
# the service back, so this script checks that the new revision is the one that
# completed. It fails when the circuit breaker rolled back.
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <cluster> <service> <task-definition-arn>" >&2
  exit 64
fi

cluster="$1"
service="$2"
task_definition="$3"

aws ecs update-service \
  --cluster "${cluster}" \
  --service "${service}" \
  --task-definition "${task_definition}" \
  --query 'service.serviceName' \
  --output text >/dev/null

desired="$(aws ecs describe-services \
  --cluster "${cluster}" \
  --services "${service}" \
  --query 'services[0].desiredCount' \
  --output text)"

if [[ "${desired}" == "0" ]]; then
  echo "::notice::${service} is disabled (desired count 0). The new revision is registered and the service points at it, but nothing was started."
  exit 0
fi

echo "Waiting for ${service} to reach a steady state..."
aws ecs wait services-stable --cluster "${cluster}" --services "${service}"

primary="$(aws ecs describe-services \
  --cluster "${cluster}" \
  --services "${service}" \
  --query 'services[0].deployments[?status==`PRIMARY`] | [0].{taskDefinition: taskDefinition, rolloutState: rolloutState}' \
  --output json)"

rollout_state="$(jq -r '.rolloutState' <<<"${primary}")"
primary_revision="$(jq -r '.taskDefinition' <<<"${primary}")"

if [[ "${primary_revision}" != "${task_definition}" || "${rollout_state}" != "COMPLETED" ]]; then
  echo "Deployment of ${service} did not complete. Primary revision: ${primary_revision}, rollout state: ${rollout_state}." >&2
  aws ecs describe-services \
    --cluster "${cluster}" \
    --services "${service}" \
    --query 'services[0].events[:8].message' \
    --output text >&2
  exit 1
fi

echo "${service} is running ${task_definition}."
