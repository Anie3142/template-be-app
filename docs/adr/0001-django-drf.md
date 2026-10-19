# ADR 0001: Django + Django REST Framework as the API stack

- Status: Accepted

## Context

The template is the starting point for small product backends that expose a JSON
API to a separate Next.js frontend. Each new app needs the same things on day one:
an ORM with migrations, an admin UI for poking at data, token authentication,
rate limiting, pagination/filtering, and machine-readable API docs the frontend
can generate types from.

## Decision

Use **Django 4.2 LTS** with **Django REST Framework** (`backend/requirements.txt`),
plus:

- `drf-spectacular` for an OpenAPI 3 schema, Swagger UI and ReDoc
  (`/api/schema/`, `/api/docs/`, `/api/redoc/`). The frontend template runs
  `openapi-typescript` against this schema.
- `django-filter` + DRF `SearchFilter` / `OrderingFilter` as default filter backends,
  page-number pagination with `PAGE_SIZE = 50`.
- Auth0 RS256 JWT validation (`apps/core/authentication.py`) as the default
  authenticator and `IsAuthenticated` as the default permission. Public endpoints
  opt out explicitly (`AllowAny` on the health check).
- Throttle scopes `user` / `anon` / `webhook`, with `DevExemptUserRateThrottle`
  skipping user throttling under `DEV_AUTH_BYPASS`.
- A custom exception handler (`apps/core/exceptions.py`) that flattens errors into
  one envelope.
- Settings split into `config/settings/{base,dev,prod}.py`.

## Consequences

- One framework covers ORM, migrations, admin and the API layer; there is little
  glue code to maintain per app.
- The OpenAPI schema is generated from serializers and viewsets, so frontend types
  stay in sync as long as `gen:api` is re-run.
- Secure by default: a new endpoint requires authentication unless it says otherwise.
- The stack is synchronous WSGI (gunicorn). Long-lived connections or heavy async I/O
  would need ASGI workers or a separate service.
- Django 4.2 is pinned `<5.0`; moving to 5.x is a deliberate upgrade.

## Alternatives considered

- **FastAPI + SQLAlchemy/Alembic:** async and fast, but admin, auth plumbing,
  filtering and migrations would each be a separate library to assemble per app.
- **Django Ninja:** lighter API layer, but DRF's throttling, filter backends and
  ecosystem (drf-spectacular, django-filter) are already what the apps rely on.
- **Node/Express or NestJS:** would share a language with the frontend but loses the
  Django admin and ORM migrations, which are the main productivity win here.
