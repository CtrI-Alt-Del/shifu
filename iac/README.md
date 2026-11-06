# Shifu AWS staging infrastructure

This directory contains two independent Terraform roots:

- `bootstrap/` creates only the private S3 backend used by staging;
- `staging/` creates the application platform in `us-east-2`.

It does not read, import, or modify the academic S3 laboratory under
`packages/iac/`. No command below is evidence that AWS resources are currently
deployed. Applying this configuration creates cost-bearing resources.

## Prerequisites and private inputs

Use Terraform `>= 1.8, < 2`, an AWS identity authorized for the declared
resources, Docker, the AWS CLI, and access to the external Inngest and Resend
configurations. Review every plan before applying it.

Copy the committed examples to ignored local files:

```powershell
Copy-Item iac/bootstrap/terraform.tfvars.example iac/bootstrap/terraform.tfvars
Copy-Item iac/staging/backend.hcl.example iac/staging/backend.hcl
Copy-Item iac/staging/terraform.tfvars.example iac/staging/terraform.tfvars
```

The Terraform inputs are non-secret: unique backend bucket name, two available
AZs/CIDRs when defaults are unsuitable, optional public hostname and existing ACM
certificate ARN (set both for HTTPS, or leave both unset for the MVP's plain HTTP
on the ALB address), immutable image tags, monthly budget amount/subscriber e-mails, teardown
mode/final snapshot identifier, and tags. Keep the local copies private even
though they must contain no credentials.

Application secret **values** never enter Terraform. Prepare these JSON keys for
out-of-band population after the metadata exists:

| Secret | Required JSON keys |
| --- | --- |
| Web | `BETTER_AUTH_DATABASE_URL`, `BETTER_AUTH_SECRET`, `SHIFU_BFF_SHARED_SECRET` |
| Server | `DATABASE_URL`, `AGENTOS_DATABASE_URL`, `REDIS_URL`, `INNGEST_EVENT_KEY`, `INNGEST_SIGNING_KEY`, `SHIFU_RESEND_API_KEY`, `SHIFU_RESEND_FROM`, `SHIFU_BFF_SHARED_SECRET`, `SHIFU_COMMUNICATION_ENCRYPTION_KEYS`, `DIAGNOSTIC_REVISION_HMAC_KEY` |
| Server, optional | `OPENROUTER_API_KEY`; set `openrouter_enabled=true` only after the key exists |

`DATABASE_URL` and `BETTER_AUTH_DATABASE_URL` use the RDS-generated master
credential. `REDIS_URL` must use TLS and AUTH. Inngest must use production
event/signing keys, and Resend must use the staging sender. Generate independent
high-entropy values for Better Auth, the BFF shared secret, communication
encryption, diagnostics, and Redis AUTH.
`AGENTOS_DATABASE_URL` must use the `shifu_agentos_runtime` role and the same
runtime password passed to the AgentOS role bootstrap in step 5.

## 1. Bootstrap remote state

The bootstrap root intentionally begins with local state and has no dependency on
staging. Review and apply it first:

```powershell
terraform -chdir=iac/bootstrap init
terraform -chdir=iac/bootstrap fmt -check -recursive
terraform -chdir=iac/bootstrap validate
terraform -chdir=iac/bootstrap plan -out=.terraform/bootstrap.tfplan
terraform -chdir=iac/bootstrap apply .terraform/bootstrap.tfplan
terraform -chdir=iac/bootstrap output
```

Put the bucket output into the ignored `iac/staging/backend.hcl`. Retain
`encrypt=true` and `use_lockfile=true`; no DynamoDB lock table is used. Initialize
staging only after the bucket is available:

```powershell
terraform -chdir=iac/staging init -reconfigure -backend-config=backend.hcl
terraform -chdir=iac/staging validate
```

Preserve the bootstrap state securely until the staging backend has been removed.

## 2. Phase zero: create the foundation with services disabled

Keep `services_enabled=false`, `purge_data=false`, and immutable non-`latest`
placeholder/deployment tags in the private staging variables. Task definitions
can be registered before those image tags exist; desired counts remain zero.

```powershell
terraform -chdir=iac/staging plan -out=.terraform/foundation.tfplan
terraform -chdir=iac/staging show .terraform/foundation.tfplan
terraform -chdir=iac/staging apply .terraform/foundation.tfplan
```

Review that the plan contains one `/16` VPC, two AZs/six subnets, no NAT Gateway,
private data services, zero desired tasks, exact ALB routing, secret metadata,
separate logs and the budget. Do not continue if a secret value or secret-version
resource appears.

## 3. Build and publish immutable images

The deploy workflow described in "Continuous delivery" does this on every merge.
To publish by hand, build both images for `linux/arm64` from the repository root.
The Web image needs the URL that browsers use to reach the server. Authenticate
Docker to the ECR registry using a non-persisted password stream, then tag and push
with the exact immutable tags selected in the variables file:

```powershell
docker buildx build --platform linux/arm64 -f apps/server/Dockerfile -t shifu-server:<immutable-tag> --load .
docker buildx build --platform linux/arm64 -f apps/web/Dockerfile --build-arg VITE_SHIFU_SERVER_URL=<server-url> -t shifu-web:<immutable-tag> --load .
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-2.amazonaws.com
docker tag shifu-server:<immutable-tag> <server-repository-url>:<immutable-tag>
docker tag shifu-web:<immutable-tag> <web-repository-url>:<immutable-tag>
docker push <server-repository-url>:<immutable-tag>
docker push <web-repository-url>:<immutable-tag>
```

Verify each tag resolves to the expected digest. Deployment tags are immutable;
publish a new tag rather than reusing one.

## 4. Populate secrets and activate Redis AUTH out of band

Use a protected temporary JSON file outside the repository (with access limited
to the operator) to write one version to each Terraform-created secret. The file
must not be printed, added to shell history, or captured in a transcript. For
example, with paths held in private environment variables:

```powershell
aws secretsmanager put-secret-value --secret-id (terraform -chdir=iac/staging output -raw web_secret_arn) --secret-string "file://$env:SHIFU_WEB_SECRET_FILE"
aws secretsmanager put-secret-value --secret-id (terraform -chdir=iac/staging output -raw server_secret_arn) --secret-string "file://$env:SHIFU_SERVER_SECRET_FILE"
```

The responses contain version metadata, not secret values. Securely erase the
operator-owned temporary files after successful population. Read the AWS-managed
RDS credential privately and construct the Web/server database URLs without displaying
either value.

Create a compliant Redis token privately and keep it only in a non-echoing private
environment variable. Activate it with ElastiCache's immediate `SET` strategy, wait
for the group to return to `available`, then clear the process variable:

```powershell
aws elasticache modify-replication-group --replication-group-id shifu-staging --auth-token $env:SHIFU_REDIS_AUTH_TOKEN --auth-token-update-strategy SET --apply-immediately
aws elasticache wait replication-group-available --replication-group-id shifu-staging
Remove-Item Env:SHIFU_REDIS_AUTH_TOKEN
```

Store the authenticated `rediss://` URL only in the server secret. Do not pass the
token to Terraform. Terraform deliberately ignores the write-only AUTH attributes
so a later plan neither stores nor removes the token.
Before enabling the server, verify through a private network path that unauthenticated
access is rejected and authenticated TLS access succeeds; do not echo the token.

Confirm every required JSON key exists. If OpenRouter is omitted, leave
`openrouter_enabled=false`; health and non-AI flows remain enabled while AI code
assessment is unavailable by its existing controlled behavior.

## 5. Create the AgentOS runtime role and run the one-off migration

Keep both service desired counts at zero. Use the `server_task_definition_arn`,
private `application_subnet_ids`, and `server_security_group_id` outputs to run one
Fargate task with the server container command overridden to:

```text
alembic upgrade head
```

Before running that task, create the least-privileged AgentOS runtime role through
a private database administration path (for example, an operator-controlled
bastion or port-forward). Run the committed
`apps/server/scripts/create_agentos_runtime_role.sql` script as the RDS master
user, passing `runtime_password` equal to the password embedded in
`AGENTOS_DATABASE_URL` and `database_name` equal to the application database.
Keep both values in non-echoing operator environment variables; never print them
or place them in Terraform state. The script is idempotent and grants only
database `CONNECT`; the migration below creates the `agentos_intelligence` and
`agentos_learning` schemas, revokes public schema creation, and grants the role
the runtime table privileges it needs.

For example, with the private connection variables and password already prepared
by the operator:

```powershell
psql $env:SHIFU_DATABASE_ADMIN_URL `
  -v ON_ERROR_STOP=1 `
  -v runtime_password="$env:SHIFU_AGENTOS_RUNTIME_ROLE_PASSWORD" `
  -v database_name="$env:SHIFU_DATABASE_NAME" `
  -f apps/server/scripts/create_agentos_runtime_role.sql
```

Verify privately that `shifu_agentos_runtime` exists before starting the
migration task. Do not enable either ECS service until the role creation and the
migration both succeed.

Supply the same `awsvpc` settings as the server service and
`assignPublicIp=ENABLED`, because staging has no NAT Gateway. This PowerShell
template uses only non-secret Terraform
outputs and writes no secret value:

```powershell
$cluster = terraform -chdir=iac/staging output -raw ecs_cluster_name
$taskDefinition = terraform -chdir=iac/staging output -raw server_task_definition_arn
$subnets = (terraform -chdir=iac/staging output -json application_subnet_ids | ConvertFrom-Json) -join ','
$securityGroup = terraform -chdir=iac/staging output -raw server_security_group_id
$network = "awsvpcConfiguration={subnets=[$subnets],securityGroups=[$securityGroup],assignPublicIp=ENABLED}"
$overrides = '{"containerOverrides":[{"name":"server","command":["alembic","upgrade","head"]}]}'
$taskArn = aws ecs run-task --cluster $cluster --task-definition $taskDefinition --launch-type FARGATE --network-configuration $network --overrides $overrides --query 'tasks[0].taskArn' --output text
aws ecs wait tasks-stopped --cluster $cluster --tasks $taskArn
aws ecs describe-tasks --cluster $cluster --tasks $taskArn --query 'tasks[0].containers[?name==`server`].{exitCode:exitCode,reason:reason}'
```

Wait for the task to stop, require container exit code zero, inspect the server log
group for a redacted migration result, and independently confirm Alembic is at
head. Never seed or reset data. If migration fails, leave services disabled,
correct image/configuration/connectivity, and rerun a new one-off task.

## 6. Enable services

Only after image digests, complete secret versions, enforced Redis AUTH, and a
successful migration are confirmed, set `services_enabled=true` and use the final
immutable tags. Review and apply the enablement plan:

```powershell
terraform -chdir=iac/staging plan -out=.terraform/enable.tfplan
terraform -chdir=iac/staging show .terraform/enable.tfplan
terraform -chdir=iac/staging apply .terraform/enable.tfplan
```

Wait for both ECS services to reach steady state and both ALB target groups to be
healthy. Circuit-breaker rollback protects a failed rollout. If a rollout fails,
set `services_enabled=false` if necessary, apply, correct the image or secret, rerun
migration when schema compatibility is uncertain, and then retry enablement.

## 7. DNS and side-effect-free smoke

With a hostname, create the operator-managed DNS alias/CNAME from it to
`alb_dns_name`; DNS is intentionally outside Terraform. Without a hostname, staging
serves plain HTTP on `alb_dns_name` and the `public_origin` output shows the URL.
Plain HTTP sends passwords and session cookies unencrypted, so use only test
accounts and set `SHIFU_USE_SECURE_COOKIES=false`, which Terraform does itself in
that mode. Without creating an account, sending e-mail, emitting an Inngest event,
or calling OpenRouter:

1. with HTTPS, confirm plain HTTP redirects to the HTTPS hostname;
2. request `<public_origin>/api/health` and expect `{"status":"ok"}` from Web;
3. inspect the server target group and confirm its private `/health` check is healthy;
4. confirm an unrelated public path does not bypass Web to reach FastAPI;
5. inspect both target groups, ECS task networking, migration revision, and the
   separate Web/server log streams;
6. inspect/synchronize the signed `/api/inngest` endpoint without sending an event;
7. confirm no response/log reveals private DNS, task addresses, credentials, or
   raw provider errors.

The smoke is infrastructure-only and does not prove e-mail delivery, job execution,
or AI assessment.

## Continuous delivery

Two GitHub Actions workflows run staging:

- `terraform-staging.yaml` checks formatting, validates and tests both roots on every
  pull request that touches `iac/`, and plans the staging root. Someone starts the
  apply by hand on `main`. It then plans again, and a reviewer approves the apply.
- `staging-deploy.yaml` runs on every merge to `main` that touches the apps. It
  builds the Web and server images for `linux/arm64`, pushes them to ECR with the
  tags `<12-character commit hash>-web` and `-server`, registers a new revision of
  each task definition, runs the database migration as a one-off task, rolls the
  server and then the Web service, and checks both target groups and
  `<public_origin>/api/health`.

Terraform owns the task definitions, secrets wiring and sizing. The deploy workflow
copies the latest task definition and changes only the image and
`SHIFU_RELEASE_VERSION`. The services ignore task definition changes in Terraform,
so an apply never moves a service back to an older image. After Terraform changes
a task definition, run the deploy workflow again to pick the change up.

### One-time setup

AWS blocks OIDC for this account, so GitHub signs in with IAM user access keys.
Terraform creates the users and their narrow policies. It never creates keys.

1. In the IAM console, create one access key for each user and keep the values
   only for the next step: `shifu-staging-deployer` for the app deploy and
   `shifu-staging-terraform` for Terraform. Delete any older key of the deployer.
2. In the GitHub repository settings, create three environments.

| Environment | Used by | Secrets | Protection |
| --- | --- | --- | --- |
| `staging` | `staging-deploy.yaml` | `AWS_STAGING_DEPLOYER_ACCESS_KEY_ID`, `AWS_STAGING_DEPLOYER_SECRET_ACCESS_KEY` | none, or branch limited to `main` |
| `staging-terraform` | Terraform validate and plan | `AWS_STAGING_TERRAFORM_ACCESS_KEY_ID`, `AWS_STAGING_TERRAFORM_SECRET_ACCESS_KEY` | none, so pull requests can plan |
| `staging-terraform-apply` | Terraform apply | the same two Terraform names | required reviewers, branch limited to `main` |

Prefer environment secrets over repository secrets. A repository secret is visible
to every workflow, so it would bypass the reviewers on the apply environment.

3. Set these non-secret variables. Read the values from `terraform output`.

| Environment | Variable | Value |
| --- | --- | --- |
| `staging` | `APPLICATION_SUBNET_IDS` | `application_subnet_ids`, joined with commas |
| `staging` | `SERVER_SECURITY_GROUP_ID` | `server_security_group_id` |
| `staging` | `PUBLIC_ORIGIN` | `public_origin` |
| `staging` | `VITE_SHIFU_SERVER_URL` | The URL browsers use to call the server |
| both Terraform environments | `STATE_BUCKET` | The bootstrap state bucket name |
| both Terraform environments | `TFVARS` | The full content of `iac/staging/terraform.tfvars` |

`TFVARS` replaces the ignored local file in CI, so it holds the same non-secret
values, including `services_enabled`. Change the variable to change those inputs.

### Failures and rollback

- **Image build fails:** nothing changed in AWS. Fix the code and merge again.
- **Migration fails:** the workflow stops before any service changes. Read the log
  lines in the job output, fix forward, and run the workflow again. Never seed or
  reset data. A missing `shifu_agentos_runtime` role is the usual first-run cause:
  create it as described in step 5.
- **Rollout fails:** the ECS circuit breaker returns the service to its previous
  revision and the workflow fails. Check the service events and the log groups
  `/ecs/shifu-staging/web` and `/ecs/shifu-staging/server`.
- **Roll back to an earlier release:** run `staging-deploy.yaml` by hand and set
  `image_sha` to the 12-character hash of an earlier deploy. It redeploys the images
  already in ECR without building. It does not undo migrations, so only roll back
  across releases whose schema changes are backward compatible.
- **Rotate a key:** create the new key, update the environment secrets, run a
  workflow, then delete the old key.

## Recovery

- **Foundation apply failure:** leave services disabled and resume from the saved
  remote state after correcting the reported resource/input.
- **Image/secret failure:** do not enable services; publish a new immutable image or
  add a new secret version, then review a fresh plan.
- **Migration failure:** inspect the stopped task/logs, fix forward, and rerun; never
  seed, reset, or auto-migrate at service startup.
- **Unhealthy deployment:** use ECS deployment events and separate target health;
  circuit-breaker rollback is automatic, while operator correction is explicit.
- **Redis AUTH drift:** keep services disabled until both the cache and server secret
  contain the coordinated token; Terraform is not the rotation mechanism.

## Teardown rehearsal and execution

Initial acceptance reviews destroy plans but does **not** apply them. Safe mode is
the default: use a new globally unique `final_snapshot_identifier`, keep
`purge_data=false`, and leave ECR `force_delete` disabled. A non-empty repository
therefore blocks accidental deletion.

```powershell
terraform -chdir=iac/staging plan -destroy -out=.terraform/safe-destroy.tfplan
terraform -chdir=iac/staging show .terraform/safe-destroy.tfplan
```

Purge is separately explicit and irreversible. Set `purge_data=true`, review that
RDS skips its final snapshot and ECR permits image deletion, then create a distinct
destroy plan. Do not apply it as part of initial acceptance:

```powershell
terraform -chdir=iac/staging plan -destroy -var="purge_data=true" -out=.terraform/purge-destroy.tfplan
terraform -chdir=iac/staging show .terraform/purge-destroy.tfplan
```

When destruction is separately authorized, destroy **staging first** by applying
exactly one of the reviewed destroy plans:

```powershell
terraform -chdir=iac/staging apply .terraform/safe-destroy.tfplan
# OR, only for separately authorized irreversible cleanup:
terraform -chdir=iac/staging apply .terraform/purge-destroy.tfplan
```

Handle retained prior snapshots only through another explicit AWS operation. After
staging destruction is complete and its state is no longer needed, empty/version-
delete the backend only under explicit purge authorization. Set
`purge_backend=true` in the private bootstrap variables, review and apply the
backend destroy last:

```powershell
terraform -chdir=iac/bootstrap plan -destroy -out=.terraform/backend-destroy.tfplan
terraform -chdir=iac/bootstrap show .terraform/backend-destroy.tfplan
terraform -chdir=iac/bootstrap apply .terraform/backend-destroy.tfplan
```

Never destroy the backend while it owns live staging state.

## Cost-bearing resources

The public ALB, Fargate tasks, RDS PostgreSQL,
ElastiCache Redis, CloudWatch logs, ECR storage/scans, Secrets Manager secrets,
public IPv4/EIP usage, S3 backend storage/requests, and external Inngest/Resend/
OpenRouter plans may incur cost. The monthly AWS Budget notifies at forecasted 80%
and actual 100%; it is not a hard spending limit. Staging intentionally uses no NAT Gateway
(tasks get public IPs), one Spot task per service when enabled, Single-AZ RDS without
automated backups, and one Redis node. It is not production-ready or highly available.
