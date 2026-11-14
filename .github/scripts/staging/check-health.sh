#!/usr/bin/env bash
# Check that staging serves traffic after a deploy.
#
# Usage: check-health.sh <cluster> <public-origin>
#
# Skips with a notice when the web service is disabled (desired count 0).
# Otherwise waits until both ALB target groups report only healthy targets and
# the public origin answers /api/health with {"status":"ok"}.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <cluster> <public-origin>" >&2
  exit 64
fi

cluster="$1"
public_origin="${2%/}"
name_prefix="${cluster}"
attempts=30
delay_seconds=10

desired="$(aws ecs describe-services \
  --cluster "${cluster}" \
  --services "${name_prefix}-web" \
  --query 'services[0].desiredCount' \
  --output text)"

if [[ "${desired}" == "0" ]]; then
  echo "::notice::Staging services are disabled, so the health check was skipped."
  exit 0
fi

target_group_healthy() {
  local name="$1" arn states
  arn="$(aws elbv2 describe-target-groups --names "${name}" \
    --query 'TargetGroups[0].TargetGroupArn' --output text)"
  states="$(aws elbv2 describe-target-health --target-group-arn "${arn}" \
    --query 'TargetHealthDescriptions[].TargetHealth.State' --output text)"
  [[ -n "${states}" && -z "$(tr '\t' '\n' <<<"${states}" | grep -v '^healthy$' || true)" ]]
}

for ((attempt = 1; attempt <= attempts; attempt++)); do
  if target_group_healthy "${name_prefix}-web" && target_group_healthy "${name_prefix}-server"; then
    body="$(curl --silent --show-error --max-time 10 "${public_origin}/api/health" || true)"
    if jq -e '.status == "ok"' <<<"${body}" >/dev/null 2>&1; then
      echo "Staging is healthy: both target groups are healthy and ${public_origin}/api/health answered ok."
      exit 0
    fi
  fi
  echo "Attempt ${attempt}/${attempts}: not healthy yet."
  sleep "${delay_seconds}"
done

echo "Staging did not become healthy in time." >&2
for group in web server; do
  arn="$(aws elbv2 describe-target-groups --names "${name_prefix}-${group}" \
    --query 'TargetGroups[0].TargetGroupArn' --output text)"
  echo "Target group ${group}:" >&2
  aws elbv2 describe-target-health --target-group-arn "${arn}" \
    --query 'TargetHealthDescriptions[].TargetHealth' --output json >&2
done
exit 1
