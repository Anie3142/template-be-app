"""Development settings."""
from .base import *  # noqa: F401,F403
from decouple import config

DEBUG = True
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# Set DEV_AUTH_BYPASS=true to bypass Auth0 and use a local test user.
# DevExemptUserRateThrottle also skips throttling when this is true.
DEV_AUTH_BYPASS = config('DEV_AUTH_BYPASS', default='true', cast=bool)

if DEV_AUTH_BYPASS:
    REST_FRAMEWORK = {
        **REST_FRAMEWORK,  # noqa: F405
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'apps.core.authentication.DevAuthentication',
        ],
    }
