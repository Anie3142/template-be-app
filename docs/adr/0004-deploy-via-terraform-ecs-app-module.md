# ADR 0004: Deploy through the shared `terraform-ecs-app` module, with a public health endpoint

- Status: Accepted

## Context

Several apps share one AWS platform: a VPC, an ECS cluster with a capacity
provider, and Traefik as the ingress router. Copying ECS task definition, service,
security group and service-discovery Terraform into every app would drift quickly.

## Decision

- `terraform/main.tf` only describes the app. It reads the shared stacks through
  `terraform_remote_state` (`live/10-network`, `live/20-ecs`, `live/27-traefik`) and
  passes their outputs to
  [`terraform-ecs-app`](https://github.com/Anie3142/terraform-ecs-app), pinned to
  `?ref=v1.0.0`.
- Each app keeps its own state at `apps/<APP_NAME>/terraform.tfstate`, with DynamoDB
  locking, configured by Jenkins at `terraform init`.
- Jenkins deploys on push to `main`: build `:<git-sha>` image, push to ECR,
  `terraform plan -out=tfplan` with `image_tag=<sha>`, `terraform apply tfplan`, then
  `aws ecs wait services-stable`. Every stage after checkout is gated on
  `APP_NAME != 'CHANGE_ME'`, so the template itself runs a green no-op.
- Images are tagged with the commit SHA, so every deploy is traceable and a rollback
  is a re-apply with an earlier `image_tag`. The module enables the ECS deployment
  circuit breaker with automatic rollback.
- `GET /api/v1/health` is public (`AllowAny`), touches no database, and returns
  `{status, version, timestamp}`. It is the target for load balancer / smoke checks;
  the Jenkins smoke-test `curl` is ready to enable once DNS resolves.

## Consequences

- Each app is about 100 lines of Terraform; platform changes ship once in the module
  and are adopted by bumping `ref`.
- Apps depend on the shared stacks' output names. Renaming an output is a breaking
  change for every app.
- GitHub Actions validates Terraform with `init -backend=false`, so CI needs no cloud
  credentials but also cannot run `plan`.
- The health endpoint proves the process is serving, not that the database is
  reachable. A readiness check that queries the DB would be a separate endpoint.
- `aws ecs wait services-stable` makes the pipeline fail when tasks crash-loop,
  rather than reporting success right after `apply`.

## Alternatives considered

- **Per-app copy of ECS resources:** maximum flexibility, but drift and duplication.
- **AWS Copilot / App Runner:** less to own, but would not reuse the existing VPC,
  cluster capacity provider and Traefik routing.
- **GitHub Actions deploy with OIDC:** keeps CI and CD in one place; Jenkins is used
  because the platform's Jenkins agents already run on ECS with a task role, so no
  cloud credentials are stored anywhere.
