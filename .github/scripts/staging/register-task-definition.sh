#!/usr/bin/env bash
# Register a new revision of an ECS task definition family with a new image.
#
# Usage: register-task-definition.sh <family> <container> <image> <release-version>
#
# Copies the latest active revision, so everything Terraform owns (secrets,
# environment, sizing, roles) is kept. Only the image and SHIFU_RELEASE_VERSION
# change. Prints the ARN of the new revision on stdout.
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <family> <container> <image> <release-version>" >&2
  exit 64
fi

family="$1"
container="$2"
image="$3"
release_version="$4"

current="$(aws ecs describe-task-definition \
  --task-definition "${family}" \
  --query taskDefinition \
  --output json)"

if ! jq -e --arg container "${container}" \
  '.containerDefinitions | any(.name == $container)' <<<"${current}" >/dev/null; then
  echo "Container '${container}' not found in task definition '${family}'." >&2
  exit 1
fi

next="$(jq \
  --arg container "${container}" \
  --arg image "${image}" \
  --arg release_version "${release_version}" '
  del(
    .taskDefinitionArn,
    .revision,
    .status,
    .requiresAttributes,
    .compatibilities,
    .registeredAt,
    .registeredBy
  )
  | .containerDefinitions |= map(
      if .name == $container then
        .image = $image
        | .environment = (
            ((.environment // []) | map(select(.name != "SHIFU_RELEASE_VERSION")))
            + [{name: "SHIFU_RELEASE_VERSION", value: $release_version}]
          )
      else . end
    )
' <<<"${current}")"

aws ecs register-task-definition \
  --cli-input-json "${next}" \
  --query taskDefinition.taskDefinitionArn \
  --output text
