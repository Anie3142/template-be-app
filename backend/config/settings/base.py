"""
Base Django settings for the template app.

Production-ready patterns baked in:
- drf-spectacular OpenAPI schema + Swagger UI
- DevExemptUserRateThrottle (skips throttling under DEV_AUTH_BYPASS=true)
- ServerTimingMiddleware (emits Server-Timing header for DevTools perf)
- CacheControlMiddleware (private browser cache on read-mostly GETs)
- Auth0 JWT authentication
"""
import os
from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'drf_spectacular',
    'corsheaders',
    'django_filters',
    # Local apps
    'apps.core',
    'apps.example',
]

MIDDLEWARE = [
    # ServerTimingMiddleware sits at the very top so its wall-clock measurement
    # captures every other middleware's overhead too.
    'apps.core.middleware.ServerTimingMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # CacheControlMiddleware tags responses on the way out — runs late on the
    # response path so the Cache-Control header survives untouched.
    'apps.core.middleware.CacheControlMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3'),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.core.authentication.Auth0JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    # DevExemptUserRateThrottle skips throttling when DEV_AUTH_BYPASS=true so
    # Playwright tests + local dev sessions don't fight for the same quota.
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.core.throttling.DevExemptUserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '2000/hour',
        'anon': '20/hour',
        'webhook': '1000/hour',
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': config('APP_NAME', default='Template API'),
    'DESCRIPTION': 'Template backend API. Replace this description in config/settings/base.py.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
}

# Auth0
AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='')
AUTH0_API_AUDIENCE = config('AUTH0_API_AUDIENCE', default='')
AUTH0_ALGORITHMS = ['RS256']

# CORS
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
CORS_ALLOW_CREDENTIALS = True
# Expose perf headers cross-origin so DevTools can render Server-Timing.
CORS_EXPOSE_HEADERS = ['Server-Timing', 'Cache-Control']

# Webhook HMAC secret (see apps/example/webhooks.py)
EXAMPLE_WEBHOOK_SECRET = config('EXAMPLE_WEBHOOK_SECRET', default='')
