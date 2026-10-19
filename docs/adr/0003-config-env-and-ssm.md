# ADR 0003: Configuration through environment variables, secrets through SSM

- Status: Accepted

## Context

The same image runs locally, in CI and on ECS. Nothing account-specific or secret
may live in the repository, which is public, and the template must be reusable by
any app without editing code.

## Decision

- All runtime settings are read with `python-decouple` `config(...)` in
  `config/settings/*.py`. `DATABASE_URL` is parsed by `dj-database-url` (SQLite
  fallback when unset, which is what tests use).
- `.env.example` lists every variable the app reads; `.env` is git-ignored.
- On ECS, plain values (`DJANGO_SETTINGS_MODULE`, `ALLOWED_HOSTS`) are set in the
  module's `environment` map, and secrets (`SECRET_KEY`, `DATABASE_URL`, webhook
  secrets) are passed as a `secrets` map of env var name to **SSM Parameter Store
  ARN**, which ECS resolves at task start.
- Terraform has no account-specific defaults: the S3 backend is a partial config
  (`backend.hcl.example`), `state_bucket` and `ecr_registry` are required variables,
  and Jenkins derives the account ID at runtime from `aws sts get-caller-identity`.
- `DEV_AUTH_BYPASS` is read only by `config/settings/dev.py`; production settings
  never load `DevAuthentication`.

## Consequences

- Secrets never appear in the image, the task definition's plain environment, or
  the repo. Rotating one is an SSM update plus a new deployment.
- A missing variable falls back to its default instead of failing. In particular,
  `base.py` falls back to an insecure `SECRET_KEY`, so production deployments must
  provide `SECRET_KEY` through `secrets` (see the production checklist in the README).
- The task execution role (from the shared ECS stack) must be allowed to read the
  referenced SSM parameters.

## Alternatives considered

- **AWS Secrets Manager:** supports automatic rotation, but costs per secret per
  month; SSM SecureString covers the current needs.
- **django-environ:** equivalent to python-decouple; no strong reason to switch.
- **Fail-fast settings (no defaults):** stricter, but makes the template harder to
  boot on a fresh clone. A good follow-up for prod settings specifically.
