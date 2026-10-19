# Changelog

All notable changes to this template. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Architecture decision records in `docs/adr/`.
- `Makefile` (`dev`, `test`, `lint`, `build`, `tf-validate`, `scan`).
- `.pre-commit-config.yaml` (ruff, terraform fmt, gitleaks).
- `SECURITY.md`, `CONTRIBUTING.md`, this changelog.
- README: production checklist and "What this template gives you".

## 2026-10-19: Public release

### Added
- GitHub Actions CI: ruff, `manage.py check`, pytest, linux/amd64 Docker build,
  `terraform fmt` / `validate`, gitleaks.
- pytest smoke tests (health, Server-Timing, webhook HMAC, dev bypass), `ruff.toml`,
  dev requirements and the initial example migration.
- `backend.hcl.example` and `terraform.tfvars.example`; MIT license.

### Changed
- Removed account-specific values: partial S3 backend config, `state_bucket` and
  `ecr_registry` variables, Jenkins resolves the AWS account ID at runtime.
- README rewritten for a public audience.

## 2026-04-15

### Fixed
- Build images for `linux/amd64` (the ECS hosts are x86_64).
- Jenkins runs plain `terraform` using the agent's task role instead of `aws2-wrap`.

## 2026-04-12

### Added
- Production-ready Django scaffold: drf-spectacular docs, Auth0 JWT + dev bypass,
  throttling, Server-Timing / Cache-Control middleware, HMAC webhook example,
  docker compose with an optional full-stack profile.

### Changed
- Jenkins build/push/deploy stages are gated on `APP_NAME != 'CHANGE_ME'`.

## 2025-12-25

### Added
- Initial Django backend template deploying through the `terraform-ecs-app` module.
