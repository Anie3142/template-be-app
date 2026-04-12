"""Custom throttle classes that exempt dev/test traffic."""
from django.conf import settings
from rest_framework.throttling import UserRateThrottle


class DevExemptUserRateThrottle(UserRateThrottle):
    """UserRateThrottle that skips throttling entirely when DEV_AUTH_BYPASS=true.

    This prevents Playwright tests + browser dev sessions from hitting limits
    on the same dev user.

    In production (DEV_AUTH_BYPASS=false), behaves exactly like UserRateThrottle.
    """

    def allow_request(self, request, view):
        if getattr(settings, 'DEV_AUTH_BYPASS', False):
            return True
        return super().allow_request(request, view)
