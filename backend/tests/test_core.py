"""Smoke tests for the template: health endpoint, middleware headers, webhook HMAC."""
import hashlib
import hmac
import json

import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


# DevAuthentication (active under DEV_AUTH_BYPASS) get_or_creates the dev user on
# every request, so even AllowAny endpoints touch the database in tests.
@pytest.mark.django_db
def test_health_check_is_public_and_healthy(client):
    response = client.get('/api/v1/health')

    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'


@pytest.mark.django_db
def test_server_timing_header_is_emitted(client):
    response = client.get('/api/v1/health')

    assert 'total;dur=' in response['Server-Timing']


@override_settings(EXAMPLE_WEBHOOK_SECRET='test-secret')
def test_webhook_rejects_bad_signature(client):
    response = client.post(
        '/api/v1/example/webhook',
        data=json.dumps({'id': 'evt_1'}),
        content_type='application/json',
        HTTP_X_SIGNATURE='not-a-valid-signature',
    )

    assert response.status_code == 401


@override_settings(EXAMPLE_WEBHOOK_SECRET='test-secret')
def test_webhook_accepts_valid_signature(client):
    body = json.dumps({'id': 'evt_1'}).encode()
    signature = hmac.new(b'test-secret', body, hashlib.sha256).hexdigest()

    response = client.post(
        '/api/v1/example/webhook',
        data=body,
        content_type='application/json',
        HTTP_X_SIGNATURE=signature,
    )

    assert response.status_code == 200
    assert response.json() == {'received': True}


@pytest.mark.django_db
def test_example_list_is_reachable_under_dev_bypass(client):
    response = client.get('/api/v1/example/parents/')

    assert response.status_code == 200
