#!/usr/bin/env bash
# Create or update the AgentOS runtime database role on staging.
#
# Usage: create-agentos-role.sh
#
# The database is private, so this runs create-agentos-role.py as a one-off Fargate
# task inside the VPC. The task uses the latest server task definition, so it has
# the server secrets. It takes its subnets and security group from the server ECS
# service. Run it again after changing the role password in the server secret.
# Needs AWS credentials for the deployer or an admin, and the region us-east-2.
set -euo pipefail

cluster="${CLUSTER:-shifu-staging}"
service="${cluster}-server"
here="$(cd "$(dirname "$0")" && pwd)"

network="$(aws ecs describe-services \
  --cluster "${cluster}" \
  --services "${service}" \
  --query 'services[0].networkConfiguration.awsvpcConfiguration' \
  --output json)"

if [[ "${network}" == "null" ]]; then
  echo "Could not read the network settings of ${service}." >&2
  exit 1
fi

subnets="$(jq -r '.subnets | join(",")' <<<"${network}")"
security_group="$(jq -r '.securityGroups[0]' <<<"${network}")"

task_definition="$(aws ecs describe-task-definition \
  --task-definition "${service}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"

exec "${here}/run-server-task.sh" \
  "${cluster}" "${task_definition}" "${subnets}" "${security_group}" \
  "/ecs/${cluster}/server" "AgentOS role setup" \
  -- python -c "$(cat "${here}/create-agentos-role.py")"
