"""Auth0 JWT authentication for Django REST Framework.

Two auth classes:

- ``Auth0JWTAuthentication`` — validates RS256 Auth0 tokens against the JWKS
  endpoint and auto-creates a Django user keyed by the ``sub`` claim.
- ``DevAuthentication`` — bypass auth entirely in dev/test mode. Wired in via
  ``config/settings/dev.py`` when ``DEV_AUTH_BYPASS=true`` so Playwright and
  local curl sessions don't need a real token.
"""
import os

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()


class DevAuthentication(authentication.BaseAuthentication):
    """Authenticate as a deterministic dev user. DO NOT USE IN PRODUCTION."""

    DEV_USERNAME_DEFAULT = 'devuser'

    def authenticate(self, request):
        dev_user_id = os.environ.get('DEV_USER_ID')
        if dev_user_id:
            try:
                return (User.objects.get(id=dev_user_id), None)
            except User.DoesNotExist:
                pass

        username = os.environ.get('DEV_USERNAME', self.DEV_USERNAME_DEFAULT)
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'},
        )
        return (user, None)


class Auth0JWTAuthentication(authentication.BaseAuthentication):
    """Validate Auth0-issued RS256 JWTs and lazily create a matching user."""

    def __init__(self):
        self.jwks_client = None

    def get_jwks_client(self):
        if not self.jwks_client:
            jwks_url = f'https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json'
            self.jwks_client = jwt.PyJWKClient(jwks_url)
        return self.jwks_client

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]

        try:
            jwks_client = self.get_jwks_client()
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=settings.AUTH0_ALGORITHMS,
                audience=settings.AUTH0_API_AUDIENCE,
                issuer=f'https://{settings.AUTH0_DOMAIN}/',
            )

            auth0_id = payload.get('sub')
            email = payload.get('email', '')

            # Key the Django user on the Auth0 sub stored in username. If you
            # need a first-class auth0_id field, add a custom user model in
            # apps.core.models and swap User here.
            user, _ = User.objects.get_or_create(
                username=auth0_id,
                defaults={'email': email},
            )

            return (user, token)

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f'Invalid token: {exc}')
        except Exception as exc:  # pragma: no cover - network/JWKS failures
            raise exceptions.AuthenticationFailed(f'Authentication failed: {exc}')
