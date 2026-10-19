# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[private vulnerability reporting](https://github.com/Anie3142/template-be-app/security/advisories/new) for this repository.
Do not open a public issue. You can expect an acknowledgement within a few days.

## Scope

This is a template. Issues in the template code itself (authentication, webhook
verification, settings defaults, CI or Terraform) are in scope. Apps created from it
are maintained by their owners.

## Built-in safeguards

- gitleaks runs in CI over the full history and as a pre-commit hook.
- `.env`, `backend.hcl`, `terraform.tfvars` and Terraform state are git-ignored.
- Production secrets are injected by ECS from SSM Parameter Store, never baked into
  the image (see `docs/adr/0003-config-env-and-ssm.md`).
- The dev authentication bypass is only wired in by `config/settings/dev.py`.
