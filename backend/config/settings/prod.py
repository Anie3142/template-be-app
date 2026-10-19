"""Production settings."""
from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)

# Cloudflare tunnel -> Traefik -> Django is HTTP internally; Cloudflare handles HTTPS.
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
