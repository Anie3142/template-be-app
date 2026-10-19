# ADR 0002: Container image, gunicorn and start-up migrations

- Status: Accepted

## Context

Apps run as ECS tasks on x86_64 hosts. The image must be small, must not run as
root, and must start the app the same way in every environment. Each app also
owns its own database schema and needs migrations applied on deploy.

## Decision

`Dockerfile`:

- **Multi-stage build.** The `builder` stage installs `build-essential` and
  `libpq-dev` and compiles wheels for `requirements.txt`. The runtime stage is
  `python:3.11-slim` with only `libpq5` and `curl`, and installs from those wheels.
- **Non-root.** A system user `app` owns `/app` and the container runs as `USER app`.
- **gunicorn** serves `config.wsgi:application` on `0.0.0.0:8000` with `--workers 2`,
  sized for the default 256 CPU / 512 MB task (`terraform/main.tf`).
- `DJANGO_SETTINGS_MODULE=config.settings.prod`, `PYTHONUNBUFFERED=1` so logs reach
  CloudWatch immediately.
- **Built for `linux/amd64`** in both Jenkins (`docker build --platform linux/amd64`)
  and GitHub Actions, because the ECS hosts are x86_64; an image built natively on
  an arm64 machine would not run there.

`docker/entrypoint.sh` runs `manage.py migrate --noinput` and
`collectstatic --noinput` before `exec`-ing the CMD. Static files are served by
WhiteNoise (`CompressedManifestStaticFilesStorage`), so no separate static host is
needed.

Local development (`docker-compose.yml`) reuses the same image but overrides the
command with `makemigrations` + `migrate` + `runserver` and bind-mounts `backend/`
for hot reload.

## Consequences

- Migrations are applied automatically on every task start. Deploys need no extra
  pipeline step, but migrations must be backwards compatible with the previous
  release (expand/contract), because old and new tasks overlap during a rolling
  deploy, and a slow migration delays the task becoming healthy.
- With `desired_count > 1`, several tasks may run `migrate` concurrently. Django
  takes no global migration lock, so for multi-task services a one-off migration
  task is the safer pattern.
- `collectstatic` failures are tolerated (`|| true`) so a misconfigured static setup
  does not block start-up; check logs if static assets 404.
- `curl` is available in the runtime image for container health probes and debugging.
- The dev compose command runs `makemigrations`, which is a convenience for a fresh
  clone. Generated migrations must still be committed.

## Alternatives considered

- **uWSGI:** more knobs, but gunicorn is simpler to configure and widely understood.
- **Uvicorn/ASGI workers:** unnecessary while all views are synchronous.
- **Migrations as a separate pipeline step or ECS run-task:** safer for multi-task
  services; deferred until an app needs more than one task.
- **Distroless or Alpine runtime:** smaller, but `psycopg2` and debugging tools are
  simpler on Debian slim.
