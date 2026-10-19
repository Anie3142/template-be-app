# template-be-app

[![CI](https://github.com/Anie3142/template-be-app/actions/workflows/ci.yml/badge.svg)](https://github.com/Anie3142/template-be-app/actions/workflows/ci.yml)

A production-shaped **Django + Django REST Framework** service template with a full
delivery path: containerised local dev, a Jenkins push-to-deploy pipeline, and
Terraform that ships the service onto a shared **AWS ECS** platform through a
reusable module ([`terraform-ecs-app`](https://github.com/Anie3142/terraform-ecs-app)).

It is the backend half of a pair. The frontend half is
[`template-fe-app`](https://github.com/Anie3142/template-fe-app) (Next.js on Cloudflare Workers). New apps are
created by copying the template, setting an app name, and replacing the example domain.

## What this template gives you

| Area | Included |
|---|---|
| API | Django 4.2 LTS + DRF, OpenAPI 3 with Swagger/ReDoc, filtering, pagination, flattened error envelope |
| Auth | Auth0 RS256 JWT validation (signature, expiry, audience, issuer); dev bypass wired only in dev settings |
| Abuse controls | `user` / `anon` / `webhook` throttle scopes; HMAC-SHA256 webhook verification that fails closed |
| Observability | `Server-Timing` header on every response, unbuffered logs to CloudWatch, public `/api/v1/health` |
| Container | Multi-stage `linux/amd64` image, non-root user, gunicorn, WhiteNoise, migrations on start |
| Delivery | GitHub Actions (lint, test, image build, Terraform validate, gitleaks) + Jenkins push-to-deploy with `ecs wait services-stable` |
| Infrastructure | ~100 lines of Terraform on a versioned shared module; SSM-backed secrets; no account IDs in the repo |
| Developer experience | `docker compose up`, `make` targets, pre-commit hooks, seed command stub, example app to copy |

Design decisions are recorded as ADRs in [`docs/adr/`](docs/adr/):
[Django + DRF](docs/adr/0001-django-drf.md) ·
[image & gunicorn](docs/adr/0002-container-image-and-gunicorn.md) ·
[config & SSM](docs/adr/0003-config-env-and-ssm.md) ·
[deploy via terraform-ecs-app](docs/adr/0004-deploy-via-terraform-ecs-app-module.md).

## Highlights

- **Platform-module consumption, not copy-paste infra.** Each app is ~100 lines of
  Terraform. It reads the shared network, ECS cluster and Traefik stacks via
  `terraform_remote_state` and hands them to a versioned module (`?ref=v1.0.0`).
- **No account-specific values in the repo.** The S3 backend is a partial config,
  the state bucket and ECR registry are variables, and Jenkins resolves the AWS
  account ID at runtime from its IAM role (`aws sts get-caller-identity`).
- **Template-safe pipeline.** Every build/push/deploy stage is gated on
  `APP_NAME != 'CHANGE_ME'`, so the template repo itself runs green as a no-op
  while any app created from it runs the full pipeline.
- **API conventions baked in:** OpenAPI 3 schema + Swagger/ReDoc (drf-spectacular),
  Auth0 RS256 JWT validation against JWKS, per-user/anon/webhook rate limits,
  HMAC-SHA256 webhook verification with constant-time compare, a flattened error
  envelope, and `Server-Timing` / `Cache-Control` middleware.
- **Hardened image.** Multi-stage build (wheels compiled in a builder stage),
  slim runtime, non-root `app` user, gunicorn as the server.

## Stack

| Layer | Choice |
|---|---|
| Language / framework | Python 3.11, Django 4.2 LTS, DRF 3.14+ |
| API docs | drf-spectacular (OpenAPI 3, Swagger UI, ReDoc) |
| Auth | Auth0 (RS256 JWT via PyJWT + JWKS), dev-mode bypass |
| Database | PostgreSQL 16 (via `DATABASE_URL`, dj-database-url); SQLite fallback for tests |
| Serving | gunicorn, WhiteNoise for static files |
| Container | Docker multi-stage, `linux/amd64` |
| CI/CD | Jenkins (deploy), GitHub Actions (lint/test/build/validate/secret scan) |
| IaC | Terraform >= 1.0, AWS provider ~> 5.0, S3 backend + DynamoDB locking |
| Runtime | AWS ECS (awsvpc, capacity provider), Traefik, Cloud Map, CloudWatch Logs, SSM |

## Architecture

```mermaid
flowchart LR
    dev[Developer] -->|git push main| scm[(Git repo)]
    scm --> jenkins[Jenkins pipeline]
    scm --> gha[GitHub Actions CI]

    subgraph CI/CD
      jenkins -->|docker build linux/amd64| img[Image :git-sha]
      img -->|docker push| ecr[(Amazon ECR)]
      jenkins -->|terraform plan/apply| tf[terraform/main.tf]
    end

    tf -->|remote state| shared[(Shared platform state:<br/>network / ecs / traefik)]
    tf -->|module terraform-ecs-app v1.0.0| svc

    subgraph AWS
      svc[ECS service<br/>task: gunicorn + Django]
      svc --> logs[CloudWatch Logs]
      svc -.->|secrets| ssm[SSM Parameter Store]
      svc --> cm[Cloud Map service discovery]
      svc --> db[(PostgreSQL)]
      traefik[Traefik] -->|Host rule from Docker labels| svc
    end

    user[Client / frontend] -->|HTTPS| edge[Edge / TLS termination] --> traefik
```

Request path inside the service:

```mermaid
flowchart LR
    req[HTTP request] --> st[ServerTimingMiddleware] --> cors[CORS] --> sec[Security / WhiteNoise / sessions / CSRF]
    sec --> auth{DRF auth}
    auth -->|prod| jwt[Auth0JWTAuthentication<br/>JWKS RS256, aud + iss checked]
    auth -->|dev, DEV_AUTH_BYPASS=true| devauth[DevAuthentication]
    jwt --> thr[Throttles: user / anon / webhook]
    devauth --> thr
    thr --> view[ViewSet / view] --> cc[CacheControlMiddleware] --> resp[Response + Server-Timing]
```

## Project layout

```
.
├── .github/workflows/ci.yml   # Lint, test, docker build, terraform validate, gitleaks
├── Jenkinsfile                # Build -> ECR -> terraform apply -> wait for ECS stable
├── Dockerfile                 # Multi-stage, non-root, gunicorn
├── docker-compose.yml         # Postgres + Django (hot reload); optional full-stack profile
├── docker/entrypoint.sh       # migrate + collectstatic, then exec CMD
├── .env.example               # Every env var the app reads
├── ruff.toml                  # Lint rules
├── Makefile                   # dev / test / lint / build / tf-validate / scan
├── .pre-commit-config.yaml    # ruff, terraform fmt, gitleaks
├── docs/adr/                  # Architecture decision records
├── backend/
│   ├── manage.py
│   ├── requirements.txt       # Runtime deps
│   ├── requirements-dev.txt   # pytest, pytest-django, ruff
│   ├── pytest.ini
│   ├── config/
│   │   ├── settings/{base,dev,prod}.py
│   │   └── urls.py            # /api/v1/..., /api/schema/, /api/docs/, /api/redoc/, /admin/
│   ├── apps/
│   │   ├── core/              # auth, throttling, middleware, exception handler, health, seed cmd
│   │   └── example/           # reference model/serializer/viewset/webhook to copy from
│   └── tests/                 # health, middleware, webhook HMAC, dev-bypass smoke tests
└── terraform/
    ├── main.tf                # Remote state lookups + terraform-ecs-app module
    ├── backend.hcl.example    # Partial S3 backend config for local init
    └── terraform.tfvars.example
```

## Local development

Prerequisites: Docker with Compose v2.

```bash
cp .env.example .env
docker compose up
```

This starts PostgreSQL 16 and Django's dev server with the `backend/` directory
bind-mounted for hot reload. On boot the container runs `makemigrations` and `migrate`.

| URL | What |
|---|---|
| http://localhost:8000/api/v1/health | Health check (public) |
| http://localhost:8000/api/docs/ | Swagger UI |
| http://localhost:8000/api/redoc/ | ReDoc |
| http://localhost:8000/api/schema/ | Raw OpenAPI schema |
| http://localhost:8000/admin/ | Django admin |

`DEV_AUTH_BYPASS=true` (the default in `.env.example`) swaps Auth0 for
`DevAuthentication`, which signs every request in as a local `devuser`, and disables
per-user throttling, so you can call authenticated endpoints with plain `curl`.

**Full stack:** with the frontend template checked out as a sibling directory
(`../frontend`), `docker compose --profile full up` also starts Next.js on
http://localhost:3000. Anonymous volumes for `/app/node_modules` and `/app/.next`
keep host and container build caches separate.

### Without Docker

```bash
cd backend
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python manage.py migrate          # SQLite if DATABASE_URL is unset
python manage.py runserver
```

### Tests and lint

```bash
make install   # inside a Python 3.11 virtualenv
make lint test
```

| Target | What it does |
|---|---|
| `make dev` | `docker compose up --build` (creates `.env` from the example if missing) |
| `make test` | pytest (SQLite, dev settings) |
| `make lint` / `make fmt` | ruff check / ruff autofix |
| `make build` | Production image for `linux/amd64` |
| `make tf-validate` | `terraform fmt -check` + `validate` with no backend |
| `make scan` | gitleaks over the git history |

`pre-commit install` enables the hooks in `.pre-commit-config.yaml`
(ruff, terraform fmt, gitleaks, whitespace/YAML checks).

## CI/CD

### GitHub Actions (`.github/workflows/ci.yml`), on every push to `main` and every PR

| Job | Steps |
|---|---|
| Lint & test | `ruff check`, `manage.py check`, `pytest` (SQLite, dev settings) |
| Docker build | Buildx build of the production image for `linux/amd64` (no push), GHA layer cache |
| Terraform | `terraform fmt -check`, `terraform init -backend=false`, `terraform validate`. No cloud credentials needed. |
| Secret scan | gitleaks over the full git history |

### Jenkins (`Jenkinsfile`): deploy on push to `main`

1. **Checkout**, then record the short commit SHA used as the image tag.
2. **Template placeholder check:** if `APP_NAME == 'CHANGE_ME'`, every later stage is skipped.
3. **Resolve AWS account** from the agent's IAM role and derive the ECR registry host.
4. **Test** (placeholder stage; GitHub Actions runs the suite).
5. **Build image:** `docker build --platform linux/amd64`, tagged `:<sha>` and `:latest`.
6. **Push to ECR:** `aws ecr get-login-password | docker login`, then push both tags.
7. **Deploy via Terraform:** `terraform init` with backend config from Jenkins env,
   `plan -out=tfplan` with `image_tag=<sha>`, then `apply tfplan`.
8. **Wait for deployment:** `aws ecs wait services-stable`.
9. **Smoke test:** the curl against `/api/v1/health` is ready to uncomment once DNS resolves.

The Jenkins controller provides `TF_STATE_BUCKET`, `TF_LOCK_TABLE`, `ECS_CLUSTER` and
`APP_DOMAIN` as global environment variables. AWS credentials come from the agent's
task role (IMDS), so the pipeline holds no long-lived keys.

## Deployment model (Terraform)

`terraform/main.tf` deploys only the app. The shared platform lives in separate
stacks, and their outputs are read from remote state:

| Remote state key | Outputs used |
|---|---|
| `live/10-network` | `vpc_id`, `private_subnet_ids`, `cloudmap_namespace_id` |
| `live/20-ecs` | `cluster_arn`, `apps_capacity_provider_name`, `task_execution_role_arn` |
| `live/27-traefik` | `traefik_security_group_id` |

The [`terraform-ecs-app`](https://github.com/Anie3142/terraform-ecs-app) module (pinned to `v1.0.0`) creates:

- an ECR repository with scan-on-push,
- an ECS task definition (`awsvpc`) whose container carries Traefik Docker labels
  (`Host(<hostname>)` router to `container_port`), CloudWatch logging and SSM-backed secrets,
- an ECS service on the cluster's capacity provider with the deployment circuit breaker
  (auto-rollback) enabled,
- a security group that admits container-port traffic from Traefik (plus the VPC CIDR when `allow_vpc_access` is on),
- a Cloud Map service for internal discovery.

Manual run:

```bash
cd terraform
cp backend.hcl.example backend.hcl            # git-ignored
cp terraform.tfvars.example terraform.tfvars  # git-ignored
terraform init -backend-config=backend.hcl
terraform plan
```

## Configuration

All runtime configuration comes from environment variables (python-decouple).

| Variable | Used by | Default | Notes |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Django | `config.settings.prod` in the image | `config.settings.dev` locally |
| `SECRET_KEY` | Django | insecure dev value | **Must** be supplied in prod via the `secrets` map (SSM) |
| `DATABASE_URL` | dj-database-url | `sqlite:///db.sqlite3` | e.g. `postgres://user:pass@host:5432/db` |
| `ALLOWED_HOSTS` | prod settings | empty | Terraform sets it to `var.hostname` |
| `DEV_AUTH_BYPASS` | dev settings | `true` | Ignored by prod settings |
| `AUTH0_DOMAIN` | JWT auth | empty | e.g. `your-tenant.us.auth0.com` |
| `AUTH0_API_AUDIENCE` | JWT auth | empty | Auth0 API identifier |
| `CORS_ALLOWED_ORIGINS` | django-cors-headers | `http://localhost:3000` | Comma-separated |
| `EXAMPLE_WEBHOOK_SECRET` | webhook | empty | Empty means every webhook is rejected |
| `SECURE_SSL_REDIRECT` | prod settings | `False` | TLS terminates at the edge in front of Traefik |
| `APP_NAME` | OpenAPI title | `Template API` | |

Terraform inputs: `app_name`, `hostname`, `image_tag`, `ecr_registry`, `state_bucket`,
`aws_region`, `cpu` (256), `memory` (512), `desired_count` (1), `secrets` (map of env
var name to SSM parameter ARN).

## Security notes

- **No secrets in the repo.** `.env`, `backend.hcl`, `terraform.tfvars` and state files
  are git-ignored. gitleaks runs in CI over the full history.
- **Secrets at runtime come from SSM Parameter Store**, injected by ECS through the
  `secrets` map. They are never baked into the image or written in plain task env.
- **Short-lived cloud credentials.** Jenkins uses its ECS task role, and terraform
  validation in GitHub Actions runs with no credentials at all.
- **JWT validation** checks signature (RS256 via JWKS), expiry, audience and issuer.
- **Dev bypass cannot leak into prod.** `DevAuthentication` is wired in only by
  `config/settings/dev.py`. `prod.py` inherits the Auth0 authenticator from `base.py`.
- **Webhooks** verify an HMAC-SHA256 signature with `hmac.compare_digest` and fail
  closed when no secret is configured. They have their own throttle scope.
- **Container** runs as a non-root user and ships only runtime libraries.
- **Prod cookies** are `Secure`, and `SECURE_PROXY_SSL_HEADER` trusts
  `X-Forwarded-Proto` from the proxy.
- **Known trade-off:** `base.py` falls back to an insecure `SECRET_KEY` when none is set.
  Production deployments must pass `SECRET_KEY` through `secrets`.

## Production checklist

Before the first real deploy of an app created from this template:

- [ ] `APP_NAME` set in `Jenkinsfile`; `app_name` / `hostname` set in `terraform/main.tf`.
- [ ] `SECRET_KEY` and `DATABASE_URL` stored in SSM and referenced in the `secrets` map
      (the code falls back to an insecure key if `SECRET_KEY` is missing).
- [ ] `AUTH0_DOMAIN` and `AUTH0_API_AUDIENCE` set; `DEV_AUTH_BYPASS` not set in prod.
- [ ] `CORS_ALLOWED_ORIGINS` limited to the real frontend origin(s).
- [ ] Webhook secrets in SSM (an empty secret rejects every webhook).
- [ ] Throttle rates in `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` reviewed for the app's traffic.
- [ ] `cpu` / `memory` / `desired_count` sized; if `desired_count > 1`, consider running
      migrations as a one-off task (see ADR 0002).
- [ ] Smoke-test `curl` in the Jenkinsfile enabled once DNS resolves.
- [ ] Migrations are backwards compatible with the running release.

## Creating an app from this template

1. `Jenkinsfile`: set `APP_NAME` (lowercase).
2. `terraform/main.tf`: set the `app_name` / `hostname` defaults and add SSM ARNs to `secrets`.
3. `.env.example`: set `AUTH0_API_AUDIENCE`, `CORS_ALLOWED_ORIGINS`, `APP_NAME`.
4. Replace `apps/example/` with real models, keeping the `select_related` and
   `TruncMonth` aggregation patterns.
5. Implement `apps/core/management/commands/seed_realistic.py` for realistic local data.

## License

[MIT](LICENSE) © Aniebiet-Abasi Udo
