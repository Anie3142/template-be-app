"""Webhook handler stub — HMAC-SHA256 signature verification.

Canonical pattern: read the raw request body, recompute the HMAC with a shared
secret, compare with ``hmac.compare_digest`` (NOT ``==``) to avoid timing
attacks. Store the shared secret in SSM, wire it in via env var
``EXAMPLE_WEBHOOK_SECRET``, and never log it.

Idempotency is the provider's responsibility + a unique constraint on the
event id in your own models. Don't rely on the HMAC check alone to dedupe.
"""
import hashlib
import hmac

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle


def _verify_signature(raw_body: bytes, provided_signature: str) -> bool:
    secret = settings.EXAMPLE_WEBHOOK_SECRET
    if not secret or not provided_signature:
        return False
    expected = hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, provided_signature)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def example_webhook(request):
    """Stub webhook endpoint. Replace the body with your provider's payload parsing."""
    example_webhook.throttle_scope = 'webhook'

    signature = request.META.get('HTTP_X_SIGNATURE', '')
    if not _verify_signature(request.body, signature):
        return Response(
            {'error': 'invalid signature'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Real handlers would parse request.data, upsert by event id, and return 200
    # so the provider stops retrying. Keep this fast — heavy work belongs in a
    # background task.
    return Response({'received': True}, status=status.HTTP_200_OK)
