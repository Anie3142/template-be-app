# Backend App Template

Production-ready Django + DRF scaffold with Auth0, drf-spectacular, performance
middleware, and push-to-deploy CI/CD to ECS. Copy this repo, rename a few
placeholders, fill in your models, and ship.

## Expected layout (sibling-checkout for full-stack dev)

When paired with a frontend app spawned from `template-fe-app`, both repos
live side-by-side under a shared parent directory:

```
~/code-repo/<app>/
├── backend/     # this repo (template-be-app)
└── frontend/    # sibling repo (template-fe-app)
```

Each is its own independent git repo with its own Jenkins pipeline. The parent
directory is NOT a git repo — it's just an organizational wrapper so
`docker compose` can see both source trees at once.

## Quick Start — two modes

Copy the env file once:

```bash
cp .env.example .env
```

**Mode 1: BE-only dev** (no frontend checked out — or you're running
`npm run dev` on the host from the sibling frontend):

```bash
docker compose up
# → db + web (Django). Visit http://localhost:8000/api/docs/
```

**Mode 2: Full-stack dev** (requires `../frontend/` sibling checkout of
`template-fe-app`):

```bash
docker compose --profile full up
# → db + web + frontend. Visit http://localhost:3000 AND http://localhost:8000
```

Then:

- **Health:** http://localhost:8000/api/v1/health
- **Swagger UI:** http://localhost:8000/api/docs/
- **Admin:** http://localhost:8000/admin/
- **Frontend landing (full profile only):** http://localhost:3000

The first boot runs migrations automatically. `DEV_AUTH_BYPASS=true` is set in
`.env.example` so you can hit authenticated endpoints without Auth0.

## What's baked in

- **drf-spectacular** OpenAPI schema at `/api/schema/`, Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/`.
- **`ServerTimingMiddleware`** — emits `Server-Timing` header on every response with `total`, `db;desc="N queries"`, `view` breakdown. Visible in DevTools → Network → Timing.
- **`CacheControlMiddleware`** — `Cache-Control: private, max-age=300` on GET responses for paths listed in `apps/core/middleware.CACHEABLE_PATHS`. Add your read-mostly paths there.
- **`DevExemptUserRateThrottle`** — `UserRateThrottle` that skips throttling entirely when `DEV_AUTH_BYPASS=true` so Playwright + browser dev sessions don't fight for the same quota.
- **`Auth0JWTAuthentication`** — validates RS256 Auth0 tokens against the JWKS endpoint, auto-creates a Django user.
- **`DevAuthentication`** — bypass wired in via `config/settings/dev.py` when `DEV_AUTH_BYPASS=true`.
- **`apps/example/`** — canonical patterns you should copy into your real app:
  - `select_related('parent')` on the viewset queryset (N+1 prevention).
  - `TruncMonth` + `Coalesce(Sum, 0)` monthly aggregation in a single query.
  - HMAC-SHA256 webhook signature verification with `hmac.compare_digest`.
- **`apps/core/management/commands/seed_realistic.py`** — stub documenting the running-balance pattern. Replace the body with your realistic seed generator.

## Structure

```
├── Dockerfile             # Multi-stage ARM64 production build
├── docker-compose.yml     # Local dev: postgres + web with hot reload
├── Jenkinsfile            # CI/CD pipeline (uses aws2wrap for terraform)
├── .env.example           # All canonical env vars
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── settings/{base,dev,prod}.py
│   │   ├── urls.py        # /api/v1/health, /api/docs, /api/schema
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/
│       ├── core/          # middleware, throttling, auth, exceptions, seed cmd
│       └── example/       # model + serializer + view + webhook stub
├── docker/
│   └── entrypoint.sh      # Runs migrate + collectstatic before CMD
└── terraform/
    └── main.tf            # Uses terraform-ecs-app module
```

## What to Change for a New App

1. `Jenkinsfile`: set `APP_NAME`.
2. `terraform/main.tf`: set `app_name`, `hostname`, backend `key`, and any SSM secrets map.
3. `.env.example`: update `AUTH0_API_AUDIENCE`, `CORS_ALLOWED_ORIGINS`, and `APP_NAME`.
4. Replace `apps/example/` with your real models (keep `select_related` + `TruncMonth` patterns).
5. Fill in `apps/core/management/commands/seed_realistic.py`.

## Workflow Rules (NON-NEGOTIABLE)

This template inherits the workflow rules from the infrastructure repo. Read
[`~/code-repo/namesless-company-infra/CLAUDE.md`](../namesless-company-infra/CLAUDE.md)
before making any infrastructure changes. Summary:

1. **Terraform-first for ALL infrastructure changes.** Anything that creates, modifies, or deletes an AWS resource goes through Terraform. Never `aws ecs update-service`, never `aws ssm put-parameter` (except Rule 5).
2. **AWS CLI is read-only.** `describe-*`, `list-*`, `get-*`, `logs`, `wait`, `sts get-caller-identity` only. Anything `create-*` / `delete-*` / `put-*` / `update-*` — STOP and use Terraform.
3. **`aws2wrap --profile default -- terraform <cmd>`** for every Terraform invocation. Plain `terraform` fails under OIDC SSO. Install: `pipx install aws2-wrap`.
4. **OIDC SSO login is interactive.** `aws sso login --profile default` opens Chrome; the agent cannot click approve. If you see expired-token errors, run that command and wait for the browser redirect.
5. **SSM secret value pattern** — Terraform creates `aws_ssm_parameter` with `lifecycle.ignore_changes = [value]`; real value set out-of-band via console or a one-time `put-parameter --overwrite`. This is the ONLY allowed exception to Rule 1.
6. **Confirm before destructive actions.** `terraform destroy`, force pushes, dropped tables, removed volumes — always ask first.

## Deployment

Push to `main` → Jenkins runs: test → build arm64 image → push to ECR → `aws2wrap -- terraform apply` → wait for ECS stable → smoke test.

- **AWS account:** 134807048528 (us-east-1)
- **State bucket:** `nameless-tf-state-134807048528`
- **Cluster:** `nameless-cluster`
- **Domain:** `https://YOUR_APP.namelesscompany.cc` (wildcard CNAME via Cloudflare Tunnel → Traefik)

## URLs

- **Dev Swagger:** http://localhost:8000/api/docs/
- **Prod app:** https://YOUR_APP.namelesscompany.cc
- **Jenkins:** https://jenkins.namelesscompany.cc
