# Contributing

1. Create a branch from `main`.
2. `make install` in a Python 3.11 virtualenv, then `pre-commit install`.
3. Make the change. Add or update tests in `backend/tests/`.
4. Run `make lint test` (and `make tf-validate` if you touched `terraform/`).
5. Open a pull request. CI must be green: lint, tests, Docker build, Terraform
   validate and secret scan.

Significant design changes should come with a new ADR in `docs/adr/`.
Never commit real account IDs, domains, tokens or `.env` files.
